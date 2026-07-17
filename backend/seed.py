"""Generates 90 days of demo SOC data: 5 partners, 20 customers, 5,000 incidents,
and 4 login users. Run from the repo root: `python backend/seed.py`.

Assumptions (documented alongside 02_SOLUTION_ARCHITECTURE_TEMPLATE.md):
- Only partner-a and partner-b carry customers/incidents (10 customers each = 20
  total) -- partner-c/d/e exist as valid partner IDs for RBAC scope testing only.
- Incident volume spikes over the last 14 days (~40% of all incidents land there)
  so the weekly trend chart shows a visible recent uptick.
- A false-positive incident never gets an opened_time, first_response_time, or
  closed_time -- it's noise that never became a tracked incident (consistent with
  Incidents = count WHERE opened_time IS NOT NULL).
- sla_result is 'none' until an incident is both opened AND closed (matches the
  MTTR-based breach rule, which needs a resolution time to evaluate against).
- service_type on an incident is denormalized from the customer's service_tier
  (Gold/Silver/Bronze) at creation time -- this is what the "Tier" filter queries.
"""

import csv
import datetime
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.core.auth import hash_password  # noqa: E402
from app.repositories.customer_repository import bulk_insert_customers  # noqa: E402
from app.repositories.db import get_connection, init_db, reset_db  # noqa: E402
from app.repositories.incident_repository import bulk_insert_incidents  # noqa: E402
from app.repositories.user_repository import create_user  # noqa: E402

random.seed(42)

PARTNERS_WITH_CUSTOMERS = ["partner-a", "partner-b"]
ALL_PARTNERS = ["partner-a", "partner-b", "partner-c", "partner-d", "partner-e"]
TIERS = ["Gold", "Silver", "Bronze"]
SIEMS = ["QRADAR", "XSIAM"]
SOARS = ["XSOAR", "Resilient"]
SEVERITIES = ["Critical", "Major", "Minor", "Informational"]
SEVERITY_WEIGHTS = [0.10, 0.30, 0.40, 0.20]
CATEGORIES = [
    "Phishing", "Malware", "Brute Force", "Data Exfiltration",
    "Privilege Escalation", "Suspicious Login", "Lateral Movement", "C2 Beacon",
]
MITRE_TECHNIQUES = [
    "T1566 Phishing", "T1059 Command and Scripting Interpreter",
    "T1110 Brute Force", "T1078 Valid Accounts", "T1041 Exfiltration Over C2",
    "T1021 Remote Services", "T1055 Process Injection", "T1071 Application Layer Protocol",
]
ANALYSTS = ["A. Rao", "K. Mehta", "S. Iyer", "J. Fernandes", "P. Shah", "R. Nair"]

NOW = datetime.datetime.now().replace(microsecond=0)
WINDOW_DAYS = 90
SPIKE_DAYS = 14
TOTAL_INCIDENTS = 5000
FALSE_POSITIVE_RATE = 0.15


def build_customers():
    customers = []
    for idx, partner in enumerate(PARTNERS_WITH_CUSTOMERS):
        for n in range(1, 11):
            customer_id = f"customer-{idx * 10 + n}"
            customers.append({
                "customer_id": customer_id,
                "customer_name": f"{partner.title().replace('-', ' ')} Customer {n}",
                "partner_id": partner,
                "service_tier": random.choice(TIERS),
                "siem": random.choice(SIEMS),
                "soar": random.choice(SOARS),
            })
    return customers


def random_created_time():
    if random.random() < 0.40:
        day_offset = random.uniform(0, SPIKE_DAYS)
    else:
        day_offset = random.uniform(0, WINDOW_DAYS)
    return NOW - datetime.timedelta(days=day_offset)


def build_incident(i, customer):
    is_false_positive = random.random() < FALSE_POSITIVE_RATE
    severity = random.choices(SEVERITIES, weights=SEVERITY_WEIGHTS, k=1)[0]
    created_time = random_created_time()
    event_time = created_time - datetime.timedelta(minutes=random.randint(5, 120))

    opened_time = first_response_time = closed_time = None
    sla_result = "none"
    status = "New"
    assigned_analyst = None

    if not is_false_positive:
        if random.random() < 0.70:
            opened_time = created_time + datetime.timedelta(minutes=random.randint(10, 60))
            first_response_time = opened_time + datetime.timedelta(minutes=random.randint(5, 120))
            assigned_analyst = random.choice(ANALYSTS)
            status = "Open"
            if random.random() < 0.60:
                closed_time = opened_time + datetime.timedelta(hours=random.uniform(2, 48))
                mttr_hours = (closed_time - opened_time).total_seconds() / 3600
                sla_result = "Breached" if (severity == "Critical" and mttr_hours > 4) else "Matched"
                status = "Closed"

    ticket_number = f"INC-{i:06d}"
    category = random.choice(CATEGORIES)
    mitre = ", ".join(random.sample(MITRE_TECHNIQUES, k=random.randint(1, 3)))
    summary = f"{severity} alert ({category}) on {customer['customer_name']}"

    return (
        ticket_number,
        customer["partner_id"],
        customer["customer_id"],
        severity,
        status,
        customer["service_tier"],
        customer["siem"],
        customer["soar"],
        sla_result,
        event_time.isoformat(),
        created_time.isoformat(),
        opened_time.isoformat() if opened_time else None,
        first_response_time.isoformat() if first_response_time else None,
        closed_time.isoformat() if closed_time else None,
        assigned_analyst,
        category,
        summary,
        mitre,
        1 if is_false_positive else 0,
    )


def export_sample_csv(rows, path):
    header = [
        "ticket_number", "partner", "customer", "severity", "status", "service_type",
        "siem", "soar", "sla_result", "event_time", "created_time", "opened_time",
        "first_response_time", "closed_time", "assigned_analyst", "category",
        "summary", "mitre_techniques", "false_positive",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows[:200])


def main():
    print("Step 1: initializing schema and clearing existing demo data")
    init_db()
    reset_db()

    print("Step 2: generating 20 customers across partner-a / partner-b")
    customers = build_customers()
    bulk_insert_customers([
        (c["customer_id"], c["customer_name"], c["partner_id"], c["service_tier"], c["siem"], c["soar"])
        for c in customers
    ])

    print(f"Step 3: generating {TOTAL_INCIDENTS} incidents over {WINDOW_DAYS} days")
    rows = [build_incident(i, random.choice(customers)) for i in range(1, TOTAL_INCIDENTS + 1)]
    bulk_insert_incidents(rows)

    sample_path = Path(__file__).resolve().parent.parent / "docs" / "incident_sample.csv"
    export_sample_csv(rows, sample_path)
    print(f"Step 3b: exported sample rows to {sample_path}")

    print("Step 4: creating 4 demo users")
    demo_users = [
        ("superadmin", "Admin@123", "super_admin", None, None),
        ("partner_mgr", "Partner@123", "partner_manager", "partner-a", None),
        ("customer_viewer", "Customer@123", "customer_viewer", "partner-a", "customer-1"),
        ("analyst", "Analyst@123", "analyst", "partner-a", None),
    ]
    for username, password, role, partner_id, customer_id in demo_users:
        create_user(username, hash_password(password), role, partner_id, customer_id)

    conn = get_connection()
    incident_count = conn.execute("SELECT COUNT(*) c FROM incidents").fetchone()["c"]
    customer_count = conn.execute("SELECT COUNT(*) c FROM customers").fetchone()["c"]
    user_count = conn.execute("SELECT COUNT(*) c FROM users").fetchone()["c"]
    conn.close()

    print(f"Done: {incident_count} incidents, {customer_count} customers, {user_count} users seeded.")


if __name__ == "__main__":
    main()
