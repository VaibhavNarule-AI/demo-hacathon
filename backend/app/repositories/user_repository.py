from app.repositories.db import get_connection


def get_user_by_username(username: str):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        return row
    finally:
        conn.close()


def create_user(username, password_hash, role, partner_id=None, customer_id=None):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash, role, partner_id, customer_id) "
            "VALUES (?, ?, ?, ?, ?)",
            (username, password_hash, role, partner_id, customer_id),
        )
        conn.commit()
    finally:
        conn.close()
