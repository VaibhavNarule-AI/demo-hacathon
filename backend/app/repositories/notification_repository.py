import datetime

from app.repositories.db import get_connection


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def insert_email_outbox(to_email, subject, body, ticket_number):
    conn = get_connection()
    try:
        now = _now()
        cursor = conn.execute(
            "INSERT INTO email_outbox (to_email, subject, body, ticket_number, status, created_at, sent_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (to_email, subject, body, ticket_number, "Sent", now, now),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM email_outbox WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return dict(row)
    finally:
        conn.close()


def insert_teams_outbox(partner_id, webhook_url_mock, payload_json, ticket_number):
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO teams_outbox (partner_id, webhook_url_mock, payload_json, ticket_number, status, created_at) "
            "VALUES (?,?,?,?,?,?)",
            (partner_id, webhook_url_mock, payload_json, ticket_number, "Sent", _now()),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM teams_outbox WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return dict(row)
    finally:
        conn.close()


def insert_notification(ticket_number, type_, message):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO notifications (ticket_number, type, message, is_read, created_at) "
            "VALUES (?,?,?,0,?)",
            (ticket_number, type_, message, _now()),
        )
        conn.commit()
    finally:
        conn.close()


def insert_audit_log(user, action, tenant_filter, details):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO audit_logs (user, action, tenant_filter, details, timestamp) VALUES (?,?,?,?,?)",
            (user, action, str(tenant_filter), details, _now()),
        )
        conn.commit()
    finally:
        conn.close()


def fetch_email_outbox(tenant_filter, limit=200):
    conn = get_connection()
    try:
        if tenant_filter.get("partner"):
            rows = conn.execute(
                """SELECT eo.* FROM email_outbox eo
                   JOIN incidents i ON i.ticket_number = eo.ticket_number
                   WHERE i.partner = ? ORDER BY eo.created_at DESC LIMIT ?""",
                (tenant_filter["partner"], limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM email_outbox ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def fetch_teams_outbox(tenant_filter, limit=200):
    conn = get_connection()
    try:
        if tenant_filter.get("partner"):
            rows = conn.execute(
                "SELECT * FROM teams_outbox WHERE partner_id = ? ORDER BY created_at DESC LIMIT ?",
                (tenant_filter["partner"], limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM teams_outbox ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def fetch_notifications(tenant_filter, limit=200):
    conn = get_connection()
    try:
        if tenant_filter.get("partner"):
            rows = conn.execute(
                """SELECT n.* FROM notifications n
                   JOIN incidents i ON i.ticket_number = n.ticket_number
                   WHERE i.partner = ? ORDER BY n.created_at DESC LIMIT ?""",
                (tenant_filter["partner"], limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM notifications ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def fetch_audit_logs(limit=200):
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
