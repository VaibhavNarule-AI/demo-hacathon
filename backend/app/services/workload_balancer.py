"""Analyst Workload Balancer -- SOC analysts get assigned tickets as they
come in, with no load-aware routing, so one analyst can end up holding 40+
open tickets while another has 8. An uneven queue is itself an SLA risk: the
overloaded analyst's tickets breach not because they're hard, but because
there's no time to reach them.

Status bands (open ticket count): >OVERLOAD_THRESHOLD -> Overloaded,
<AVAILABLE_THRESHOLD -> Available, else Balanced.

Recommendation: for each Overloaded analyst, paired with the most-available
Available analyst, suggest moving enough tickets to bring both to roughly
the midpoint of their combined load -- capped so the receiving analyst never
crosses back over OVERLOAD_THRESHOLD.

Working-hours/shift capacity is a fixed constant here (STANDARD_CAPACITY)
rather than a dedicated DB-backed schedule -- there's no analysts/shift
table in this build. A production version would resolve capacity per
analyst from a real shift-config table; documented as a follow-up, not
faked as if it were already there.
"""

import datetime

from app.repositories.incident_repository import fetch_analyst_mttr, fetch_analyst_open_stats

STANDARD_CAPACITY = 20
OVERLOAD_THRESHOLD = 30
AVAILABLE_THRESHOLD = 10
MTTR_LOOKBACK_DAYS = 30


def compute_workload(tenant_filter: dict) -> dict:
    now = datetime.datetime.now(datetime.timezone.utc)
    since = (now - datetime.timedelta(days=MTTR_LOOKBACK_DAYS)).isoformat()

    open_stats = fetch_analyst_open_stats(tenant_filter)
    mttr_by_analyst = fetch_analyst_mttr(tenant_filter, since)

    analysts = []
    for name, stats in open_stats.items():
        open_count = stats["open_count"]
        if open_count > OVERLOAD_THRESHOLD:
            status = "Overloaded"
        elif open_count < AVAILABLE_THRESHOLD:
            status = "Available"
        else:
            status = "Balanced"

        analysts.append({
            "analyst": name,
            "open_tickets": open_count,
            "critical_tickets": stats["critical_count"],
            "pending_tickets": stats["pending_count"],
            "avg_mttr_h": round(mttr_by_analyst.get(name, 0.0), 1),
            "capacity": STANDARD_CAPACITY,
            "load_pct": round(open_count / STANDARD_CAPACITY * 100),
            "status": status,
        })

    analysts.sort(key=lambda a: a["open_tickets"], reverse=True)

    overloaded = [a for a in analysts if a["status"] == "Overloaded"]
    available = sorted((a for a in analysts if a["status"] == "Available"), key=lambda a: a["open_tickets"])

    recommendations = []
    available_pool = list(available)
    for over in overloaded:
        if not available_pool:
            break
        target = available_pool.pop(0)
        midpoint = round((over["open_tickets"] + target["open_tickets"]) / 2)
        move_count = min(
            over["open_tickets"] - midpoint,
            OVERLOAD_THRESHOLD - 1 - target["open_tickets"],
        )
        if move_count <= 0:
            continue
        before_ratio = over["open_tickets"] / STANDARD_CAPACITY
        after_ratio = (over["open_tickets"] - move_count) / STANDARD_CAPACITY
        estimated_improvement_pct = round((before_ratio - after_ratio) / before_ratio * 50)
        recommendations.append({
            "from_analyst": over["analyst"],
            "to_analyst": target["analyst"],
            "move_count": move_count,
            "estimated_sla_improvement_pct": estimated_improvement_pct,
            "reason": (
                f"{over['analyst']} is at {over['open_tickets']} open tickets "
                f"(capacity {STANDARD_CAPACITY}); {target['analyst']} has headroom "
                f"at {target['open_tickets']}."
            ),
        })

    return {"analysts": analysts, "recommendations": recommendations}
