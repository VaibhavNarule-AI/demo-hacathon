from app.repositories.db import get_connection


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
        clauses.append("customer = ?")
        params.append(query_filters["customer"])

    if query_filters.get("siem"):
        clauses.append("siem = ?")
        params.append(query_filters["siem"])
    if query_filters.get("soar"):
        clauses.append("soar = ?")
        params.append(query_filters["soar"])
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
