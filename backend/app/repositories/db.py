import sqlite3

from app.core.config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('super_admin','partner_manager','customer_viewer','analyst')),
    partner_id TEXT,
    customer_id TEXT
);

CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id TEXT UNIQUE NOT NULL,
    customer_name TEXT NOT NULL,
    partner_id TEXT NOT NULL,
    service_tier TEXT NOT NULL CHECK(service_tier IN ('Gold','Silver','Bronze')),
    siem TEXT NOT NULL CHECK(siem IN ('QRADAR','XSIAM')),
    soar TEXT NOT NULL CHECK(soar IN ('XSOAR','Resilient'))
);

-- partner/customer columns (not partner_id/customer_id) are the historical names
-- every repository, service, and frontend component already reads/writes --
-- same relationship the new spec describes, kept as-is rather than renamed
-- across ~15 files for no functional change.
CREATE TABLE IF NOT EXISTS incidents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_number TEXT UNIQUE NOT NULL,
    partner TEXT NOT NULL,
    customer TEXT NOT NULL,
    severity TEXT NOT NULL CHECK(severity IN ('Critical','Major','Minor','Informational')),
    status TEXT NOT NULL,
    service_type TEXT NOT NULL,
    siem TEXT NOT NULL,
    soar TEXT NOT NULL,
    sla_result TEXT CHECK(sla_result IN ('Matched','Breached','none')),
    event_time TEXT NOT NULL,
    created_time TEXT NOT NULL,
    opened_time TEXT,
    first_response_time TEXT,
    closed_time TEXT,
    assigned_analyst TEXT,
    category TEXT,
    summary TEXT,
    mitre_techniques TEXT,
    false_positive INTEGER NOT NULL DEFAULT 0,
    assignee TEXT,
    escalation_level INTEGER NOT NULL DEFAULT 0,
    escalated_at TEXT,
    snoozed_until TEXT,
    snooze_count INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_incidents_created ON incidents(created_time);
CREATE INDEX IF NOT EXISTS idx_incidents_partner ON incidents(partner);
CREATE INDEX IF NOT EXISTS idx_incidents_customer ON incidents(customer);

CREATE TABLE IF NOT EXISTS partners (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    partner_name TEXT NOT NULL,
    partner_id TEXT UNIQUE NOT NULL,
    contact_email TEXT,
    teams_webhook_url_mock TEXT,
    created_at TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS sla_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    partner_id TEXT NOT NULL,
    customer_id TEXT,
    severity TEXT NOT NULL CHECK(severity IN ('Critical','Major','Minor')),
    sla_minutes INTEGER NOT NULL,
    created_by TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS email_outbox (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    to_email TEXT NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    ticket_number TEXT,
    status TEXT NOT NULL DEFAULT 'Sent',
    created_at TEXT NOT NULL,
    sent_at TEXT
);

CREATE TABLE IF NOT EXISTS teams_outbox (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    partner_id TEXT NOT NULL,
    webhook_url_mock TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    ticket_number TEXT,
    status TEXT NOT NULL DEFAULT 'Sent',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_number TEXT,
    type TEXT NOT NULL CHECK(type IN ('Email','Teams','AutoEscalate')),
    message TEXT NOT NULL,
    is_read INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user TEXT,
    action TEXT NOT NULL,
    tenant_filter TEXT,
    details TEXT,
    timestamp TEXT NOT NULL
);
"""


def _column_names(conn, table):
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _migrate(conn) -> None:
    """Idempotent, additive migration for DBs created before these columns/
    tables existed. CREATE TABLE IF NOT EXISTS above only handles brand-new
    databases -- an existing SQLite file needs explicit ALTER TABLE for
    anything added to a table that already exists on disk."""
    tables = {row["name"] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}

    if "users" in tables:
        cols = _column_names(conn, "users")
        if "username" in cols and "email" not in cols:
            conn.execute("ALTER TABLE users RENAME COLUMN username TO email")

    if "incidents" in tables:
        cols = _column_names(conn, "incidents")
        for col, ddl in [
            ("assignee", "ALTER TABLE incidents ADD COLUMN assignee TEXT"),
            ("escalation_level", "ALTER TABLE incidents ADD COLUMN escalation_level INTEGER NOT NULL DEFAULT 0"),
            ("escalated_at", "ALTER TABLE incidents ADD COLUMN escalated_at TEXT"),
            ("snoozed_until", "ALTER TABLE incidents ADD COLUMN snoozed_until TEXT"),
            ("snooze_count", "ALTER TABLE incidents ADD COLUMN snooze_count INTEGER NOT NULL DEFAULT 0"),
        ]:
            if col not in cols:
                conn.execute(ddl)

    if "partners" in tables:
        cols = _column_names(conn, "partners")
        if "teams_webhook_url_mock" not in cols:
            conn.execute("ALTER TABLE partners ADD COLUMN teams_webhook_url_mock TEXT")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    conn = get_connection()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
        _migrate(conn)
        conn.commit()
    finally:
        conn.close()


def reset_db() -> None:
    conn = get_connection()
    try:
        conn.executescript(
            "DELETE FROM incidents; DELETE FROM customers; DELETE FROM users; "
            "DELETE FROM partners; DELETE FROM sla_configs; "
            "DELETE FROM email_outbox; DELETE FROM teams_outbox; "
            "DELETE FROM notifications; DELETE FROM audit_logs;"
        )
        conn.commit()
    finally:
        conn.close()
