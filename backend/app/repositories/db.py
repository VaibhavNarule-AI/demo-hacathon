import sqlite3

from app.core.config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
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
    false_positive INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_incidents_created ON incidents(created_time);
CREATE INDEX IF NOT EXISTS idx_incidents_partner ON incidents(partner);
CREATE INDEX IF NOT EXISTS idx_incidents_customer ON incidents(customer);
"""


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
    finally:
        conn.close()


def reset_db() -> None:
    conn = get_connection()
    try:
        conn.executescript(
            "DELETE FROM incidents; DELETE FROM customers; DELETE FROM users;"
        )
        conn.commit()
    finally:
        conn.close()
