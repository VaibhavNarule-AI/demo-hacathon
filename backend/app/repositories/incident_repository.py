from app.repositories.db import get_connection


def _eq_or_in(column: str, value: str):
    """value may be a single id or a comma-separated list (multi-select
    customer filter) -- either way, always parameterized, never interpolated."""
    values = [v for v in value.split(",") if v]
    if len(values) > 1:
        placeholders = ",".join("?" * len(values))
        return f"{column} IN ({placeholders})", values
    return f"{column} = ?", values


def build_where(query_filters: dict, tenant_filter: dict):
    """Build a parameterized WHERE clause. Tenant scope always wins over a
    request's own partner/customer query params -- it is never overridden,
    only ever narrowed further by the caller's other filters."""
    clauses = []
    params = []

    if "partner" in tenant_filter:
        clauses.append("partner = ?")
        params.append(tenant_filter["partner"])
    elif query_filters.get("partner"):
        clauses.append("partner = ?")
        params.append(query_filters["partner"])

    if "customer" in tenant_filter:
        clauses.append("customer = ?")
        params.append(tenant_filter["customer"])
    elif query_filters.get("customer"):
        clause, values = _eq_or_in("customer", query_filters["customer"])
        clauses.append(clause)
        params.extend(values)

    if query_filters.get("siem"):
        clause, values = _eq_or_in("siem", query_filters["siem"])
        clauses.append(clause)
        params.extend(values)
    if query_filters.get("soar"):
        clause, values = _eq_or_in("soar", query_filters["soar"])
        clauses.append(clause)
        params.extend(values)
    if query_filters.get("tier"):
        clauses.append("service_type = ?")
        params.append(query_filters["tier"])
    if query_filters.get("date_from"):
        clauses.append("created_time >= ?")
        params.append(query_filters["date_from"])
    if query_filters.get("date_to"):
        clauses.append("created_time <= ?")
        params.append(query_filters["date_to"])

    where_sql = " AND ".join(clauses) if clauses else "1=1"
    return where_sql, params


def fetch_incidents(query_filters: dict, tenant_filter: dict, limit: int = 200):
    where_sql, params = build_where(query_filters, tenant_filter)
    conn = get_connection()
    try:
        rows = conn.execute(
            f"SELECT * FROM incidents WHERE {where_sql} ORDER BY created_time DESC LIMIT ?",
            (*params, limit),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def fetch_open_incidents(tenant_filter: dict):
    """All currently-open incidents (opened, not yet closed) in tenant scope --
    deliberately not date-range-bound, since breach risk is about right now,
    not about whatever historical window the dashboard filter happens to be
    set to."""
    where_sql, params = build_where({}, tenant_filter)
    conn = get_connection()
    try:
        rows = conn.execute(
            f"""SELECT * FROM incidents
                WHERE {where_sql} AND opened_time IS NOT NULL AND closed_time IS NULL""",
            params,
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def fetch_recent_breach_counts(tenant_filter: dict, since_iso: str) -> dict:
    """customer -> count of Breached incidents in the last N days, batched once
    instead of one query per open incident in the breach-risk computation."""
    where_sql, params = build_where({}, tenant_filter)
    conn = get_connection()
    try:
        rows = conn.execute(
            f"""SELECT customer, COUNT(*) c FROM incidents
                WHERE {where_sql} AND sla_result = 'Breached' AND created_time >= ?
                GROUP BY customer""",
            (*params, since_iso),
        ).fetchall()
        return {r["customer"]: r["c"] for r in rows}
    finally:
        conn.close()


def fetch_all_for_analytics(query_filters: dict, tenant_filter: dict):
    """No LIMIT -- analytics needs the full matching set to aggregate correctly."""
    where_sql, params = build_where(query_filters, tenant_filter)
    conn = get_connection()
    try:
        rows = conn.execute(
            f"SELECT * FROM incidents WHERE {where_sql}", params
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_incident_by_id(incident_id: int, tenant_filter: dict):
    where_sql, params = build_where({}, tenant_filter)
    conn = get_connection()
    try:
        row = conn.execute(
            f"SELECT * FROM incidents WHERE id = ? AND {where_sql}",
            (incident_id, *params),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def bulk_insert_incidents(rows: list[tuple]) -> None:
    conn = get_connection()
    try:
        conn.executemany(
            """INSERT INTO incidents
               (ticket_number, partner, customer, severity, status, service_type,
                siem, soar, sla_result, event_time, created_time, opened_time,
                first_response_time, closed_time, assigned_analyst, category,
                summary, mitre_techniques, false_positive)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            rows,
        )
        conn.commit()
    finally:
        conn.close()


def next_ticket_number(year: int) -> str:
    """SENT-<year>-<n>, starting at 1001 for the first live-created ticket of
    that year -- a separate namespace from the seeded INC-###### tickets."""
    conn = get_connection()
    try:
        count = conn.execute(
            "SELECT COUNT(*) c FROM incidents WHERE ticket_number LIKE ?",
            (f"SENT-{year}-%",),
        ).fetchone()["c"]
        return f"SENT-{year}-{1001 + count}"
    finally:
        conn.close()


def create_incident(incident: dict) -> dict:
    conn = get_connection()
    try:
        cursor = conn.execute(
            """INSERT INTO incidents
               (ticket_number, partner, customer, severity, status, service_type,
                siem, soar, sla_result, event_time, created_time, opened_time,
                first_response_time, closed_time, assigned_analyst, category,
                summary, mitre_techniques, false_positive)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                incident["ticket_number"],
                incident["partner"],
                incident["customer"],
                incident["severity"],
                incident["status"],
                incident["service_type"],
                incident["siem"],
                incident["soar"],
                incident["sla_result"],
                incident["event_time"],
                incident["created_time"],
                incident["opened_time"],
                incident["first_response_time"],
                incident["closed_time"],
                incident["assigned_analyst"],
                incident["category"],
                incident["summary"],
                incident["mitre_techniques"],
                incident["false_positive"],
            ),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM incidents WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
        return dict(row)
    finally:
        conn.close()


def close_incident_row(incident_id: int, tenant_filter: dict, closed_time: str, sla_result: str, resolution_notes):
    """Tenant-scoped close -- the WHERE clause is the same one every other
    read/write in this repository goes through, so a partner_manager can't
    close a ticket outside their own scope any more than they can read one."""
    where_sql, params = build_where({}, tenant_filter)
    conn = get_connection()
    try:
        cursor = conn.execute(
            f"""UPDATE incidents
                SET closed_time = ?, status = 'Closed', sla_result = ?,
                    summary = CASE WHEN ? IS NOT NULL AND ? != ''
                                   THEN summary || ' | Resolution: ' || ?
                                   ELSE summary END
                WHERE id = ? AND {where_sql}""",
            (closed_time, sla_result, resolution_notes, resolution_notes or "", resolution_notes, incident_id, *params),
        )
        conn.commit()
        if cursor.rowcount == 0:
            return None
        row = conn.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,)).fetchone()
        return dict(row)
    finally:
        conn.close()


def snooze_incident_row(incident_id: int, tenant_filter: dict, snoozed_until: str, comment):
    where_sql, params = build_where({}, tenant_filter)
    conn = get_connection()
    try:
        cursor = conn.execute(
            f"""UPDATE incidents
                SET snoozed_until = ?, snooze_count = snooze_count + 1,
                    summary = CASE WHEN ? IS NOT NULL AND ? != ''
                                   THEN summary || ' | Snooze note: ' || ?
                                   ELSE summary END
                WHERE id = ? AND {where_sql}""",
            (snoozed_until, comment, comment or "", comment, incident_id, *params),
        )
        conn.commit()
        if cursor.rowcount == 0:
            return None
        row = conn.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,)).fetchone()
        return dict(row)
    finally:
        conn.close()
