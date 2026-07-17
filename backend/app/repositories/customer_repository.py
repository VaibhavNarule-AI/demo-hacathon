from app.repositories.db import get_connection


def fetch_customers(tenant_filter: dict):
    clauses = []
    params = []
    if tenant_filter.get("partner"):
        clauses.append("partner_id = ?")
        params.append(tenant_filter["partner"])
    if tenant_filter.get("customer"):
        clauses.append("customer_id = ?")
        params.append(tenant_filter["customer"])
    where_sql = " AND ".join(clauses) if clauses else "1=1"

    conn = get_connection()
    try:
        rows = conn.execute(
            f"SELECT * FROM customers WHERE {where_sql} ORDER BY customer_name", params
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_customer(customer_id: str):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM customers WHERE customer_id = ?", (customer_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def bulk_insert_customers(rows: list[tuple]) -> None:
    conn = get_connection()
    try:
        conn.executemany(
            "INSERT INTO customers (customer_id, customer_name, partner_id, service_tier, siem, soar) "
            "VALUES (?,?,?,?,?,?)",
            rows,
        )
        conn.commit()
    finally:
        conn.close()
