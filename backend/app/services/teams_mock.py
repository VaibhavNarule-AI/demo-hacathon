"""Zero-third-party Teams mock: no Teams SDK, no webhook POST over the network
-- writes a MessageCard-shaped JSON payload to disk and a teams_outbox row.
"""

import datetime
import json
from pathlib import Path

from app.repositories.notification_repository import insert_notification, insert_teams_outbox
from app.repositories.partner_repository import get_partner

TEAMS_OUTBOX_DIR = Path("/tmp/teams")


def send_teams_mock(incident: dict, trigger_type: str, time_left_str: str = "") -> dict:
    partner = get_partner(incident["partner"])
    webhook_url = (partner or {}).get("teams_webhook_url_mock") or f"https://teams.mock/{incident['partner']}"

    payload = {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "themeColor": "FF0000",
        "title": f"{incident['severity']} — {incident['ticket_number']} — {trigger_type}",
        "text": incident.get("summary", ""),
        "facts": [
            {"name": "Customer", "value": incident["customer"]},
            {"name": "SLA", "value": incident.get("sla_target_minutes", "n/a")},
            {"name": "Time Left", "value": time_left_str},
            {"name": "Link", "value": f"http://sentinelops.local/incidents/{incident['ticket_number']}"},
        ],
    }
    payload_json = json.dumps(payload, indent=2)

    outbox_row = insert_teams_outbox(incident["partner"], webhook_url, payload_json, incident["ticket_number"])

    TEAMS_OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
    json_path = TEAMS_OUTBOX_DIR / f"{incident['ticket_number']}_{trigger_type}.json"
    json_path.write_text(payload_json)

    insert_notification(incident["ticket_number"], "Teams", payload["title"])

    from app.core.auth import write_flow_log
    write_flow_log(f"TEAMS MOCK sent - {incident['ticket_number']} ({trigger_type}) -> {webhook_url} [{json_path}]")

    return outbox_row
