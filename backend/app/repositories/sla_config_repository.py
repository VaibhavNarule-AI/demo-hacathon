import datetime

from app.repositories.db import get_connection

DEFAULT_SLA_MINUTES = {"Critical": 240, "Major": 480, "Minor": 1440}


def fetch_sla_configs(tenant_filter: dict):
    conn = get_connection()
    try:
        if tenant_filter.get("partner"):
            rows = conn.execute(
                "SELECT * FROM sla_configs WHERE partner_id = ? ORDER BY id DESC",
                (tenant_filter["partner"],),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM sla_configs ORDER BY id DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def fetch_sla_configs_for_partner(partner_id: str):
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM sla_configs WHERE partner_id = ? ORDER BY id DESC", (partner_id,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def upsert_sla_config(partner_id: str, customer_id, severity: str, sla_minutes: int, created_by: str):
    conn = get_connection()
    try:
        if customer_id:
            existing = conn.execute(
                "SELECT id FROM sla_configs WHERE partner_id = ? AND customer_id = ? AND severity = ?",
                (partner_id, customer_id, severity),
            ).fetchone()
        else:
            existing = conn.execute(
                "SELECT id FROM sla_configs WHERE partner_id = ? AND customer_id IS NULL AND severity = ?",
                (partner_id, severity),
            ).fetchone()

        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        if existing:
            conn.execute(
                "UPDATE sla_configs SET sla_minutes = ?, created_by = ?, created_at = ? WHERE id = ?",
                (sla_minutes, created_by, now, existing["id"]),
            )
            row_id = existing["id"]
        else:
            cursor = conn.execute(
                "INSERT INTO sla_configs (partner_id, customer_id, severity, sla_minutes, created_by, created_at) "
                "VALUES (?,?,?,?,?,?)",
                (partner_id, customer_id, severity, sla_minutes, created_by, now),
            )
            row_id = cursor.lastrowid
        conn.commit()
        row = conn.execute("SELECT * FROM sla_configs WHERE id = ?", (row_id,)).fetchone()
        return dict(row)
    finally:
        conn.close()


def build_sla_lookup(tenant_filter: dict):
    """Returns (customer_specific, partner_default) lookup dicts for fast
    per-incident resolution without a query per row."""
    configs = fetch_sla_configs(tenant_filter)
    customer_specific = {}
    partner_default = {}
    for c in configs:
        if c["customer_id"]:
            customer_specific[(c["partner_id"], c["customer_id"], c["severity"])] = c["sla_minutes"]
        else:
            partner_default[(c["partner_id"], c["severity"])] = c["sla_minutes"]
    return customer_specific, partner_default


def resolve_sla_minutes(customer_specific, partner_default, partner_id, customer_id, severity):
    if (partner_id, customer_id, severity) in customer_specific:
        return customer_specific[(partner_id, customer_id, severity)]
    if (partner_id, severity) in partner_default:
        return partner_default[(partner_id, severity)]
    return DEFAULT_SLA_MINUTES.get(severity)
