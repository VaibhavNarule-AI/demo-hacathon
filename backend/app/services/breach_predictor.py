"""SLA Breach Predictor -- forward-looking, not backward-looking. The KPI
`sla_result` in analytics_service tells you what already breached; this tells
you what's *about to*, while there's still time to act on it.

risk_score = pct_of_sla_elapsed*0.6 + severity_weight*0.3 + breach_history*0.1
  - severity_weight: Critical=30, Major=20, Minor=10 (Informational has no SLA
    target and is never scored)
  - breach_history: count of this customer's Breached incidents in the last 30
    days * 5 -- a customer with a track record of breaches is inherently
    riskier even at the same elapsed pct

status:
  - BREACHED if time_left < 0 -- already happened, not a prediction anymore
  - BLINKING if time_left <= 5 min (Critical) or <= 15 min (Major) -- the
    signal that drives the war-room banner and the blinking ticket chip
  - HIGH if risk_score > 75, MEDIUM 50-75, else LOW
"""

import datetime

from app.repositories.incident_repository import fetch_open_incidents, fetch_recent_breach_counts
from app.repositories.sla_config_repository import build_sla_lookup, resolve_sla_minutes

SEVERITY_WEIGHT = {"Critical": 30, "Major": 20, "Minor": 10}
BLINK_THRESHOLD_MINUTES = {"Critical": 5, "Major": 15}
HIGH_RISK_SCORE = 75
MEDIUM_RISK_SCORE = 50
BREACH_HISTORY_LOOKBACK_DAYS = 30


def _parse(dt_str):
    dt = datetime.datetime.fromisoformat(dt_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt


def format_remaining(remaining_minutes: float) -> str:
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
    since = (now - datetime.timedelta(days=BREACH_HISTORY_LOOKBACK_DAYS)).isoformat()
    breach_counts = fetch_recent_breach_counts(tenant_filter, since)

    results = []
    for r in rows:
        severity_weight = SEVERITY_WEIGHT.get(r["severity"])
        if severity_weight is None:
            continue  # Informational -- no SLA target, never scored

        target_minutes = resolve_sla_minutes(
            customer_specific, partner_default, r["partner"], r["customer"], r["severity"]
        )
        opened_time = _parse(r["opened_time"])
        elapsed_minutes = (now - opened_time).total_seconds() / 60
        remaining_minutes = target_minutes - elapsed_minutes
        pct = min(elapsed_minutes / target_minutes * 100, 999)

        breach_history = breach_counts.get(r["customer"], 0)
        risk_score = pct * 0.6 + severity_weight * 0.3 + (breach_history * 5) * 0.1

        blink_threshold = BLINK_THRESHOLD_MINUTES.get(r["severity"])
        blinking_critical = blink_threshold is not None and 0 <= remaining_minutes <= blink_threshold

        snoozed_until = r["snoozed_until"]
        is_snoozed = bool(snoozed_until) and _parse(snoozed_until) > now
        if is_snoozed:
            # Snoozed tickets stop blinking/alerting until the snooze expires --
            # auto_action.check_breaches() resets snoozed_until once it's past,
            # at which point blinking resumes on its own.
            blinking_critical = False

        if is_snoozed:
            risk = "SNOOZED"
        elif remaining_minutes < 0:
            risk = "BREACHED"
        elif blinking_critical:
            risk = "BLINKING"
        elif risk_score > HIGH_RISK_SCORE:
            risk = "HIGH"
        elif risk_score >= MEDIUM_RISK_SCORE:
            risk = "MEDIUM"
        else:
            risk = "LOW"

        results.append({
            "incident_id": r["id"],
            "ticket_number": r["ticket_number"],
            "customer": r["customer"],
            "partner": r["partner"],
            "severity": r["severity"],
            "elapsed_mins": round(elapsed_minutes),
            "sla_target_minutes": target_minutes,
            "pct": round(pct, 1),
            "risk_score": round(risk_score, 1),
            "risk": risk,
            "breaches_in": format_remaining(remaining_minutes),
            "remaining_minutes": round(remaining_minutes, 1),
            "blinking_critical": blinking_critical,
            "assignee": r.get("assignee"),
            "escalation_level": r.get("escalation_level", 0),
            "snoozed_until": r.get("snoozed_until"),
        })

    results.sort(key=lambda x: x["risk_score"], reverse=True)
    return results
