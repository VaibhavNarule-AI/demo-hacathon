from app.repositories.db import get_connection


def get_user_by_email(email: str):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()
        return row
    finally:
        conn.close()


def fetch_all_users():
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, email, role, partner_id, customer_id FROM users ORDER BY id"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def fetch_emails_by_role(role: str):
    conn = get_connection()
    try:
        rows = conn.execute("SELECT email FROM users WHERE role = ?", (role,)).fetchall()
        return [r["email"] for r in rows]
    finally:
        conn.close()


def create_user(email, password_hash, role, partner_id=None, customer_id=None):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO users (email, password_hash, role, partner_id, customer_id) "
            "VALUES (?, ?, ?, ?, ?)",
            (email, password_hash, role, partner_id, customer_id),
        )
        conn.commit()
    finally:
        conn.close()
