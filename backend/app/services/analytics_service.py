"""All KPI math lives here, and only here. Repositories return raw rows;
this module turns rows into the 9 KPIs + week-over-week deltas + weekly trends.
See 02_SOLUTION_ARCHITECTURE_TEMPLATE.md for the formula-by-formula assumptions
this file implements.

v2: all timestamps are UTC-aware internally (the DB stores UTC; the frontend
converts to the viewer's chosen timezone for display only -- filtering always
happens in UTC). Ranges are capped at MAX_RANGE_DAYS for query performance,
and trend bucket size scales with the requested range so a 7-day view isn't
squeezed into the same weekly buckets as a 3-month view.
"""

import datetime

from app.repositories.incident_repository import fetch_all_for_analytics

SEVERITY_TO_P = {"Critical": "p1", "Major": "p2", "Minor": "p3"}
MAX_RANGE_DAYS = 90


class RangeTooLargeError(Exception):
    pass


def _parse(dt_str):
    if not dt_str:
        return None
    dt = datetime.datetime.fromisoformat(dt_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt


def _now():
    return datetime.datetime.now(datetime.timezone.utc)


def _avg(values):
    values = [v for v in values if v is not None]
    if not values:
        return None
    return sum(values) / len(values)


def validate_range(date_from: datetime.datetime, date_to: datetime.datetime) -> None:
    if (date_to - date_from).days > MAX_RANGE_DAYS:
        raise RangeTooLargeError(
            f"Range limited to {MAX_RANGE_DAYS} days ({MAX_RANGE_DAYS // 30} months) for performance"
        )


def _compute_raw(rows: list[dict]) -> dict:
    alerts = len(rows)
    critical_alerts = sum(1 for r in rows if r["severity"] == "Critical")
    incidents = sum(1 for r in rows if r["opened_time"])

    mttd_minutes = []
    mttr_hours = []
    response_minutes = {"p1": [], "p2": [], "p3": []}
    matched = 0
    breached = 0
    false_positives = 0

    for r in rows:
        event_time = _parse(r["event_time"])
        created_time = _parse(r["created_time"])
        opened_time = _parse(r["opened_time"])
        first_response_time = _parse(r["first_response_time"])
        closed_time = _parse(r["closed_time"])

        if event_time and created_time:
            mttd_minutes.append((created_time - event_time).total_seconds() / 60)

        if opened_time and closed_time:
            mttr_hours.append((closed_time - opened_time).total_seconds() / 3600)

        if r["sla_result"] == "Matched":
            matched += 1
        elif r["sla_result"] == "Breached":
            breached += 1

        if r["false_positive"]:
            false_positives += 1

        p_bucket = SEVERITY_TO_P.get(r["severity"])
        if p_bucket and opened_time and first_response_time:
            response_minutes[p_bucket].append(
                (first_response_time - opened_time).total_seconds() / 60
            )

    sla_denom = matched + breached
    sla_compliance_pct = (matched / sla_denom * 100) if sla_denom > 0 else None
    false_positive_rate_pct = (false_positives / alerts * 100) if alerts > 0 else None

    return {
        "alerts": alerts,
        "critical_alerts": critical_alerts,
        "incidents": incidents,
        "avg_mttd_minutes": _avg(mttd_minutes),
        "avg_mttr_hours": _avg(mttr_hours),
        "sla_compliance_pct": sla_compliance_pct,
        "sla_breaches": breached,
        "false_positive_rate_pct": false_positive_rate_pct,
        "p1_avg_response_minutes": _avg(response_minutes["p1"]),
        "p2_avg_response_minutes": _avg(response_minutes["p2"]),
        "p3_avg_response_minutes": _avg(response_minutes["p3"]),
    }


def _delta_pct(current, previous):
    if current is None or previous is None or previous == 0:
        return None
    return (current - previous) / previous * 100


def resolve_range(query_filters: dict):
    """Parse date_from/date_to (defaulting to the last 90 days), validate
    against MAX_RANGE_DAYS, and return UTC-aware (date_from, date_to). Shared
    by KPIs, trends, and the incidents list so all three panels agree on what
    a filter range means and enforce the same performance cap."""
    frm = query_filters.get("date_from")
    to = query_filters.get("date_to")
    if frm and to:
        date_from, date_to = _parse(frm), _parse(to)
    else:
        date_to = _now()
        date_from = date_to - datetime.timedelta(days=90)
    validate_range(date_from, date_to)
    return date_from, date_to


def compute_kpis(query_filters: dict, tenant_filter: dict) -> dict:
    date_from, date_to = resolve_range(query_filters)
    prev_from = date_from - datetime.timedelta(days=7)
    prev_to = date_to - datetime.timedelta(days=7)

    current_filters = {**query_filters, "date_from": date_from.isoformat(), "date_to": date_to.isoformat()}
    previous_filters = {**query_filters, "date_from": prev_from.isoformat(), "date_to": prev_to.isoformat()}

    current_rows = fetch_all_for_analytics(current_filters, tenant_filter)
    previous_rows = fetch_all_for_analytics(previous_filters, tenant_filter)

    current = _compute_raw(current_rows)
    previous = _compute_raw(previous_rows)

    result = {}
    for key in current:
        result[key] = {
            "value": current[key],
            "previous": previous[key],
            "delta_pct": _delta_pct(current[key], previous[key]),
        }
    return result


def _bucket_days_for_range(total_days: float) -> int:
    """Bucket size scales with the requested range: 7d -> daily, 30d -> weekly,
    ~3mo -> bi-weekly, beyond that -> monthly."""
    if total_days <= 7:
        return 1
    if total_days <= 30:
        return 7
    if total_days <= 100:
        return 14
    return 30


def compute_trends(metric: str, query_filters: dict, tenant_filter: dict, bucket: str = "auto") -> list[dict]:
    date_from, date_to = resolve_range(query_filters)
    if bucket == "daily":
        bucket_days = 1
    else:
        bucket_days = _bucket_days_for_range((date_to - date_from).total_seconds() / 86400)

    points = []
    cursor = date_from
    while cursor < date_to:
        bucket_end = min(cursor + datetime.timedelta(days=bucket_days), date_to)
        bucket_filters = {
            **query_filters,
            "date_from": cursor.isoformat(),
            "date_to": bucket_end.isoformat(),
        }
        rows = fetch_all_for_analytics(bucket_filters, tenant_filter)
        raw = _compute_raw(rows)

        if metric == "volume":
            values = {"alerts": raw["alerts"], "incidents": raw["incidents"]}
        else:  # mttr
            values = {
                "avg_mttr_hours": raw["avg_mttr_hours"],
                "sla_compliance_pct": raw["sla_compliance_pct"],
            }

        points.append({"week_start": cursor.date().isoformat(), "values": values})
        cursor = bucket_end

    return points
