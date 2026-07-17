"""Customer Health Score -- the number an account manager actually needs
walking into a QBR (quarterly business review): one score per customer,
30-day lookback, weighted by what actually erodes trust (SLA breaches worst,
then noise, then slow resolution).
"""

import datetime

from app.repositories.customer_repository import fetch_customers
from app.repositories.incident_repository import fetch_all_for_analytics

LOOKBACK_DAYS = 30
BREACH_WEIGHT = 12
FP_RATE_WEIGHT = 0.6
MTTR_WEIGHT = 1.5


def _parse(dt_str):
    dt = datetime.datetime.fromisoformat(dt_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt


def _top_issue(breaches: int, fp_rate: float, avg_mttr_h: float) -> str:
    if breaches > 0:
        return f"{breaches} SLA breach{'es' if breaches != 1 else ''}"
    if fp_rate > 20:
        return f"{fp_rate:.0f}% false-positive rate"
    if avg_mttr_h > 12:
        return f"MTTR {avg_mttr_h:.1f}h"
    return "No major issues"


def compute_customer_health(tenant_filter: dict) -> list[dict]:
    now = datetime.datetime.now(datetime.timezone.utc)
    since = now - datetime.timedelta(days=LOOKBACK_DAYS)
    customers = fetch_customers(tenant_filter)

    results = []
    for c in customers:
        filters = {
            "customer": c["customer_id"],
            "date_from": since.isoformat(),
            "date_to": now.isoformat(),
        }
        rows = fetch_all_for_analytics(filters, tenant_filter)

        alerts = len(rows)
        breaches = sum(1 for r in rows if r["sla_result"] == "Breached")
        false_positives = sum(1 for r in rows if r["false_positive"])
        fp_rate = (false_positives / alerts * 100) if alerts > 0 else 0.0

        mttr_values = [
            (_parse(r["closed_time"]) - _parse(r["opened_time"])).total_seconds() / 3600
            for r in rows
            if r["opened_time"] and r["closed_time"]
        ]
        avg_mttr_h = sum(mttr_values) / len(mttr_values) if mttr_values else 0.0

        health = 100 - (breaches * BREACH_WEIGHT) - (fp_rate * FP_RATE_WEIGHT) - (avg_mttr_h * MTTR_WEIGHT)
        health = max(0, min(100, round(health, 1)))

        if health > 80:
            status = "Healthy"
        elif health >= 50:
            status = "At Risk"
        else:
            status = "Critical"

        results.append({
            "customer_id": c["customer_id"],
            "customer_name": c["customer_name"],
            "partner_id": c["partner_id"],
            "health_score": health,
            "status": status,
            "breaches": breaches,
            "fp_rate": round(fp_rate, 1),
            "avg_mttr_h": round(avg_mttr_h, 1),
            "alerts": alerts,
            "top_issue": _top_issue(breaches, fp_rate, avg_mttr_h),
        })

    results.sort(key=lambda x: x["health_score"])
    return results
