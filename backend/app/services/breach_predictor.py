"""SLA Breach Predictor -- forward-looking, not backward-looking. The KPI
`sla_result` in analytics_service tells you what already breached; this tells
you what's *about to*, while there's still time to act on it.

SLA targets default to the P1/P2/P3 buckets already used for the Avg Response
KPI: Critical=P1=4h, Major=P2=8h, Minor=P3=24h -- but a partner_manager or
super_admin can override the target per partner or per customer via
/api/sla-config (see sla_config_repository). Informational has no SLA target
(same reason it's excluded from the P1/P2/P3 KPI) and is never at risk of
"breaching" something that was never promised.

An incident already past 100% of its target is labeled BREACHED, not HIGH --
it isn't a prediction anymore, and folding stale already-breached tickets into
the "act now, still time" HIGH-risk count would both be misleading and dilute
the signal for the handful of incidents actually worth an analyst's attention
right now.

blinking_critical is a separate, narrower flag: Critical with <=5 min left, or
Major with <=15 min left. That's what drives the war-room-style blinking UI --
deliberately tighter than the HIGH-risk threshold so it only fires for the
handful of tickets seconds away from breaching.
"""

import datetime

from app.repositories.incident_repository import fetch_open_incidents
from app.repositories.sla_config_repository import build_sla_lookup, resolve_sla_minutes

HIGH_RISK_PCT = 70
MEDIUM_RISK_PCT = 50
BLINK_THRESHOLD_MINUTES = {"Critical": 5, "Major": 15}


def _parse(dt_str):
    dt = datetime.datetime.fromisoformat(dt_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt


def _format_remaining(remaining_minutes: float) -> str:
    if remaining_minutes <= 0:
        return f"{abs(round(remaining_minutes))} min overdue"
    if remaining_minutes >= 60:
        hours = int(remaining_minutes // 60)
        mins = round(remaining_minutes % 60)
        return f"{hours}h {mins}m left"
    return f"{round(remaining_minutes)} min left"


def compute_breach_risk(tenant_filter: dict) -> list[dict]:
    now = datetime.datetime.now(datetime.timezone.utc)
    rows = fetch_open_incidents(tenant_filter)
    customer_specific, partner_default = build_sla_lookup(tenant_filter)

    results = []
    for r in rows:
        target_minutes = resolve_sla_minutes(
            customer_specific, partner_default, r["partner"], r["customer"], r["severity"]
        )
        if target_minutes is None:
            continue  # Informational -- no SLA target, never "at risk"

        opened_time = _parse(r["opened_time"])
        elapsed_minutes = (now - opened_time).total_seconds() / 60
        remaining_minutes = target_minutes - elapsed_minutes
        pct = min(elapsed_minutes / target_minutes * 100, 999)

        if pct >= 100:
            risk = "BREACHED"
        elif pct > HIGH_RISK_PCT:
            risk = "HIGH"
        elif pct >= MEDIUM_RISK_PCT:
            risk = "MEDIUM"
        else:
            risk = "LOW"

        blink_threshold = BLINK_THRESHOLD_MINUTES.get(r["severity"])
        blinking_critical = blink_threshold is not None and 0 <= remaining_minutes <= blink_threshold

        results.append({
            "incident_id": r["id"],
            "ticket_number": r["ticket_number"],
            "customer": r["customer"],
            "partner": r["partner"],
            "severity": r["severity"],
            "elapsed_mins": round(elapsed_minutes),
            "sla_target_minutes": target_minutes,
            "pct": round(pct, 1),
            "risk": risk,
            "breaches_in": _format_remaining(remaining_minutes),
            "remaining_minutes": round(remaining_minutes, 1),
            "blinking_critical": blinking_critical,
        })

    results.sort(key=lambda x: x["pct"], reverse=True)
    return results
