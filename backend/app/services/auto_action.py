"""Auto-action background service -- pure asyncio.sleep(60) loop, no celery,
no task queue. Runs from a FastAPI startup task and checks every 60 seconds
for open incidents that have breached (or are still snoozed past their time)
and takes action without a human in the loop.
"""

import asyncio
import datetime

from app.core.auth import write_flow_log
from app.repositories.db import get_connection
from app.repositories.notification_repository import insert_notification
from app.repositories.sla_config_repository import build_sla_lookup, resolve_sla_minutes
from app.services.breach_predictor import BLINK_THRESHOLD_MINUTES, format_remaining
from app.services.email_mock import send_email_mock
from app.services.teams_mock import send_teams_mock

CHECK_INTERVAL_SECONDS = 60
FOLLOWUP_THRESHOLD_MINUTES = 10


def _already_notified(conn, ticket_number, trigger_substring):
    row = conn.execute(
        "SELECT id FROM notifications WHERE ticket_number = ? AND message LIKE ?",
        (ticket_number, f"%{trigger_substring}%"),
    ).fetchone()
    return row is not None


def _parse(dt_str):
    dt = datetime.datetime.fromisoformat(dt_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt


def _reset_expired_snoozes(conn, now):
    rows = conn.execute(
        "SELECT id, ticket_number FROM incidents WHERE snoozed_until IS NOT NULL AND snoozed_until < ?",
        (now.isoformat(),),
    ).fetchall()
    for r in rows:
        conn.execute("UPDATE incidents SET snoozed_until = NULL WHERE id = ?", (r["id"],))
        write_flow_log(f"SNOOZE EXPIRED - {r['ticket_number']} resumed blinking")
    if rows:
        conn.commit()


def check_breaches() -> None:
    """Synchronous body, called from the async loop below. Kept sync so it
    reuses the same stdlib sqlite3 connection as the rest of the app -- this
    runs once a minute, a blocking round trip here isn't worth an async driver."""
    now = datetime.datetime.now(datetime.timezone.utc)
    conn = get_connection()
    try:
        _reset_expired_snoozes(conn, now)

        open_rows = [
            dict(r)
            for r in conn.execute(
                "SELECT * FROM incidents WHERE opened_time IS NOT NULL AND closed_time IS NULL"
            ).fetchall()
        ]
        customer_specific, partner_default = build_sla_lookup({})

        for r in open_rows:
            if r["severity"] not in ("Critical", "Major", "Minor"):
                continue

            target_minutes = resolve_sla_minutes(
                customer_specific, partner_default, r["partner"], r["customer"], r["severity"]
            )
            opened_time = _parse(r["opened_time"])
            elapsed_minutes = (now - opened_time).total_seconds() / 60
            remaining_minutes = target_minutes - elapsed_minutes

            blink_threshold = BLINK_THRESHOLD_MINUTES.get(r["severity"])
            is_blinking = blink_threshold is not None and 0 <= remaining_minutes <= blink_threshold
            not_snoozed = not (r["snoozed_until"] and _parse(r["snoozed_until"]) > now)
            if is_blinking and not_snoozed and not _already_notified(conn, r["ticket_number"], "Blinking"):
                time_left_str = format_remaining(remaining_minutes)
                try:
                    send_email_mock(r, "Blinking", time_left_str)
                    send_teams_mock(r, "Blinking", time_left_str)
                    write_flow_log(f"BLINKING NOTIFY - {r['ticket_number']} ({time_left_str})")
                except Exception as exc:
                    write_flow_log(f"BLINKING notify failed for {r['ticket_number']}: {exc}")

            if remaining_minutes <= 0 and r["escalation_level"] == 0:
                conn.execute(
                    "UPDATE incidents SET escalation_level = 1, escalated_at = ?, assignee = 'super_admin' "
                    "WHERE id = ?",
                    (now.isoformat(), r["id"]),
                )
                conn.commit()
                write_flow_log(f"AUTO-ESCALATE - {r['ticket_number']} breached, escalated to super_admin")
                try:
                    send_email_mock(r, "Escalated", "0m (breached)")
                    send_teams_mock(r, "Escalated", "0m (breached)")
                except Exception as exc:  # mock I/O must never crash the loop
                    write_flow_log(f"AUTO-ESCALATE notify failed for {r['ticket_number']}: {exc}")
                insert_notification(
                    r["ticket_number"], "AutoEscalate",
                    f"{r['ticket_number']} auto-escalated to super_admin after SLA breach",
                )

            elif remaining_minutes <= -FOLLOWUP_THRESHOLD_MINUTES and r["escalation_level"] == 1:
                followup_ticket = f"FOLLOWUP-{r['ticket_number']}"
                existing = conn.execute(
                    "SELECT id FROM incidents WHERE ticket_number = ?", (followup_ticket,)
                ).fetchone()
                if not existing:
                    conn.execute(
                        """INSERT INTO incidents
                           (ticket_number, partner, customer, severity, status, service_type, siem, soar,
                            sla_result, event_time, created_time, opened_time, first_response_time,
                            closed_time, assigned_analyst, category, summary, mitre_techniques,
                            false_positive, assignee, escalation_level, escalated_at, snoozed_until,
                            snooze_count)
                           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (
                            followup_ticket, r["partner"], r["customer"], r["severity"], "Open",
                            r["service_type"], r["siem"], r["soar"], "none", now.isoformat(),
                            now.isoformat(), now.isoformat(), None, None, None, r["category"],
                            f"Follow-up for breached {r['ticket_number']}", r["mitre_techniques"], 0,
                            "super_admin", 0, None, None, 0,
                        ),
                    )
                    write_flow_log(f"AUTO-FOLLOWUP - {followup_ticket} created for breached {r['ticket_number']}")
                conn.execute("UPDATE incidents SET escalation_level = 2 WHERE id = ?", (r["id"],))
                conn.commit()
    finally:
        conn.close()


async def auto_action_loop():
    while True:
        try:
            check_breaches()
        except Exception as exc:
            write_flow_log(f"AUTO-ACTION loop error: {exc}")
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
