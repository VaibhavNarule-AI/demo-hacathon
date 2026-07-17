"""Smart Incident Priority Score -- severity alone doesn't tell an analyst
which open ticket to work next: two Critical incidents can carry very
different real business risk. This ranks every open incident 0-100 on five
weighted factors instead of the single severity field.

priority_score = severity*0.40 + sla_urgency*0.25 + tier*0.15 + age*0.10 + repeat*0.10

Each factor is normalized to 0-100 before weighting:
  - severity:     Critical=100, Major=65, Minor=35, Informational=10
  - sla_urgency:  % of this incident's SLA window already elapsed, capped 100
                  (reuses the same target-minutes resolution as the Breach
                  Predictor, so the two features never disagree with each
                  other about a ticket's SLA clock)
  - tier:         Gold=100, Silver=60, Bronze=30 -- read straight off the
                  incident's own `service_type` (denormalized from the
                  customer at creation time), no customer-table join needed
  - age:          incident age in hours / 48h, capped 100 -- a ticket open
                  2+ days is maximally "aged" regardless of severity
  - repeat:       count of same customer+category incidents in the last 7
                  days, capped at 4+ -> 100 -- catches a repeated-attack
                  pattern a single-incident view can't see

label / recommended_action bands: >=85 Critical Priority / Investigate
Immediately, >=60 High / Investigate Soon, >=35 Medium / Monitor Closely,
else Low / Standard Queue.
"""

import datetime

from app.repositories.incident_repository import fetch_open_incidents, fetch_recent_incident_counts
from app.repositories.sla_config_repository import build_sla_lookup, resolve_sla_minutes

SEVERITY_SCORE = {"Critical": 100, "Major": 65, "Minor": 35, "Informational": 10}
TIER_SCORE = {"Gold": 100, "Silver": 60, "Bronze": 30}

WEIGHT_SEVERITY = 0.40
WEIGHT_SLA = 0.25
WEIGHT_TIER = 0.15
WEIGHT_AGE = 0.10
WEIGHT_REPEAT = 0.10

MAX_AGE_HOURS_FOR_FULL_SCORE = 48
REPEAT_LOOKBACK_DAYS = 7
REPEAT_COUNT_FOR_FULL_SCORE = 4

BAND_CRITICAL = 85
BAND_HIGH = 60
BAND_MEDIUM = 35


def _parse(dt_str):
    dt = datetime.datetime.fromisoformat(dt_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt


def _label_and_action(score: float):
    if score >= BAND_CRITICAL:
        return "Critical Priority", "Investigate Immediately"
    if score >= BAND_HIGH:
        return "High Priority", "Investigate Soon"
    if score >= BAND_MEDIUM:
        return "Medium Priority", "Monitor Closely"
    return "Low Priority", "Standard Queue"


def compute_priority_scores(tenant_filter: dict) -> list[dict]:
    now = datetime.datetime.now(datetime.timezone.utc)
    rows = fetch_open_incidents(tenant_filter)
    if not rows:
        return []

    customer_specific, partner_default = build_sla_lookup(tenant_filter)
    since = (now - datetime.timedelta(days=REPEAT_LOOKBACK_DAYS)).isoformat()
    repeat_counts = fetch_recent_incident_counts(tenant_filter, since)

    results = []
    for r in rows:
        target_minutes = resolve_sla_minutes(
            customer_specific, partner_default, r["partner"], r["customer"], r["severity"]
        )
        if target_minutes is None:
            continue  # Informational -- no SLA target, same convention as the Breach Predictor

        severity_score = SEVERITY_SCORE.get(r["severity"], 10)
        opened_time = _parse(r["opened_time"])
        elapsed_minutes = (now - opened_time).total_seconds() / 60
        remaining_minutes = target_minutes - elapsed_minutes
        sla_score = max(0.0, min(100.0, elapsed_minutes / target_minutes * 100))

        tier_score = TIER_SCORE.get(r["service_type"], 30)

        created_time = _parse(r["created_time"])
        age_hours = (now - created_time).total_seconds() / 3600
        age_score = max(0.0, min(100.0, age_hours / MAX_AGE_HOURS_FOR_FULL_SCORE * 100))

        repeat_count = repeat_counts.get((r["customer"], r["category"]), 1)
        repeat_score = max(0.0, min(100.0, (repeat_count - 1) / (REPEAT_COUNT_FOR_FULL_SCORE - 1) * 100))

        priority_score = round(
            severity_score * WEIGHT_SEVERITY
            + sla_score * WEIGHT_SLA
            + tier_score * WEIGHT_TIER
            + age_score * WEIGHT_AGE
            + repeat_score * WEIGHT_REPEAT
        )
        priority_score = max(0, min(100, priority_score))
        label, action = _label_and_action(priority_score)

        reasons = [r["severity"]]
        if remaining_minutes <= 0:
            reasons.append("SLA already breached")
        elif remaining_minutes <= 240:
            hours = int(remaining_minutes // 60)
            mins = round(remaining_minutes % 60)
            reasons.append(f"SLA expires in {hours}h {mins}m" if hours else f"SLA expires in {mins}m")
        if r["service_type"] in ("Gold",):
            reasons.append(f"{r['service_type']} Customer")
        if repeat_count > 1:
            reasons.append(f"Repeated {r['category']} activity ({repeat_count} in {REPEAT_LOOKBACK_DAYS}d)")
        if age_hours > 24:
            reasons.append(f"Open {round(age_hours / 24, 1)} days")

        results.append({
            "incident_id": r["id"],
            "ticket_number": r["ticket_number"],
            "customer": r["customer"],
            "partner": r["partner"],
            "severity": r["severity"],
            "service_type": r["service_type"],
            "priority_score": priority_score,
            "priority_label": label,
            "recommended_action": action,
            "reasons": reasons,
            # Unrounded -- a caller re-weighting these (e.g. the test suite,
            # recomputing the composite independently) needs the exact values
            # the score was built from, not a display-rounded approximation
            # that would round-trip to a different composite.
            "factors": {
                "severity": severity_score,
                "sla_urgency": sla_score,
                "customer_tier": tier_score,
                "incident_age": age_score,
                "repeat_incident": repeat_score,
            },
        })

    results.sort(key=lambda x: x["priority_score"], reverse=True)
    return results
