import datetime

from app.repositories.db import get_connection


def create_partner(partner_name: str, partner_id: str, contact_email: str, teams_webhook_url_mock: str = None):
    conn = get_connection()
    try:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        webhook = teams_webhook_url_mock or f"https://teams.mock/{partner_id}"
        conn.execute(
            "INSERT INTO partners (partner_name, partner_id, contact_email, teams_webhook_url_mock, created_at, is_active) "
            "VALUES (?,?,?,?,?,1)",
            (partner_name, partner_id, contact_email, webhook, now),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM partners WHERE partner_id = ?", (partner_id,)).fetchone()
        return dict(row)
    finally:
        conn.close()


def get_partner(partner_id: str):
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM partners WHERE partner_id = ?", (partner_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def fetch_partners():
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT p.*, COUNT(c.id) AS customer_count
               FROM partners p
               LEFT JOIN customers c ON c.partner_id = p.partner_id
               GROUP BY p.id
               ORDER BY p.created_at DESC"""
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def fetch_partner_customers(partner_id: str):
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM customers WHERE partner_id = ? ORDER BY customer_name", (partner_id,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def create_customer_for_partner(partner_id, customer_id, customer_name, service_tier, siem, soar):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO customers (customer_id, customer_name, partner_id, service_tier, siem, soar) "
            "VALUES (?,?,?,?,?,?)",
            (customer_id, customer_name, partner_id, service_tier, siem, soar),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM customers WHERE customer_id = ?", (customer_id,)).fetchone()
        return dict(row)
    finally:
        conn.close()
