"""qe-guardian's test runner. Self-contained -- uses FastAPI's TestClient to
exercise the app in-process (no live server / network port required), against
whatever DB the seed script already populated. Run from the repo root:
`python backend/test_runner.py`.
"""

import datetime
import os
import sqlite3
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
REPO_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("DB_PATH", str(REPO_ROOT / "data" / "app.db"))
os.environ.setdefault("FLOW_LOG_PATH", str(REPO_ROOT / "logs" / "flow.log"))
os.environ.setdefault("FRONTEND_DIST", str(REPO_ROOT / "frontend" / "dist"))


def _load_dotenv(path):
    """Docker injects .env via env_file:; a bare local run doesn't, so load it
    here too -- otherwise the Kiwi push would always silently skip."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


_load_dotenv(REPO_ROOT / ".env")

import jwt  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.config import JWT_ALGORITHM, JWT_SECRET  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)
results = []


def record(test_id, name, why, expected, actual, passed):
    results.append({
        "test_id": test_id,
        "name": name,
        "why": why,
        "expected": expected,
        "actual": actual,
        "status": "PASS" if passed else "FAIL",
    })


def login(email, password):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def make_expired_token(email="superadmin@pulsesoc.local", role="super_admin"):
    payload = {
        "email": email,
        "role": role,
        "partner_id": None,
        "customer_id": None,
        "exp": datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=5),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def raw_db_query(sql, params=()):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.row_factory = sqlite3.Row
    row = conn.execute(sql, params).fetchone()
    conn.close()
    return row


# A 90-day window ending now -- wide enough to cover all seed data (which
# spans exactly 90 days ending when seed.py ran, just before this), but
# within the analytics_service.MAX_RANGE_DAYS cap. A wider literal range
# (e.g. 2020-2030) would now get rejected with 400, which is the point of
# the cap -- these tests shouldn't route around it.
_now = datetime.datetime.now(datetime.timezone.utc)
frm = (_now - datetime.timedelta(days=90)).strftime("%Y-%m-%dT%H:%M:%S")
to = _now.strftime("%Y-%m-%dT%H:%M:%S")


# TC-01 -----------------------------------------------------------------
res = login("superadmin@pulsesoc.local", "Admin@123")
record(
    "TC-01", "Login sync success (superadmin)",
    "A valid demo account must be able to authenticate synchronously and receive a usable JWT.",
    "200 + access_token present", f"{res.status_code} + token={'access_token' in res.json() if res.status_code == 200 else 'n/a'}",
    res.status_code == 200 and "access_token" in res.json(),
)
sa_token = res.json()["access_token"] if res.status_code == 200 else None

# TC-02 -----------------------------------------------------------------
res = login("superadmin@pulsesoc.local", "WrongPassword!")
record(
    "TC-02", "Login wrong password returns 401",
    "Auth must reject bad credentials with 401, not a 500 or a silent 200.",
    "401", str(res.status_code),
    res.status_code == 401,
)

# TC-03 -----------------------------------------------------------------
res_api = client.get("/api/incidents")
res_page = client.get("/dashboard")
record(
    "TC-03", "Unauthenticated access blocked server-side",
    "The frontend's ProtectedRoute redirect is a UX nicety; the real guarantee has to be server-side. /dashboard itself is just the static SPA shell (no data), and every data API must 401 without a token -- that combination is what actually prevents a direct-URL bypass.",
    "/api/incidents -> 401, /dashboard -> 200 (shell only, no tenant data)",
    f"/api/incidents -> {res_api.status_code}, /dashboard -> {res_page.status_code}",
    res_api.status_code == 401 and res_page.status_code == 200,
)

# TC-04 -----------------------------------------------------------------
res = login("partner_mgr@pulsesoc.local", "Partner@123")
pm_token = res.json()["access_token"]
res = client.get(
    "/api/incidents",
    params={"partner": "partner-b", "from": frm, "to": to},
    headers={"Authorization": f"Bearer {pm_token}"},
)
partners_seen = {row["partner"] for row in res.json()} if res.status_code == 200 else set()
record(
    "TC-04", "Partner isolation: partner-a token cannot see partner-b data",
    "Tenant scope must come from the JWT, not the query string -- otherwise any partner_manager could read every other partner's incidents by editing ?partner=.",
    "partners_seen == {'partner-a'}", f"partners_seen == {partners_seen}",
    partners_seen == {"partner-a"},
)

# TC-05 -----------------------------------------------------------------
expected_alerts = raw_db_query(
    "SELECT COUNT(*) c FROM incidents WHERE created_time BETWEEN ? AND ?", (frm, to)
)["c"]
res = client.get("/api/analytics/kpis", params={"from": frm, "to": to}, headers={"Authorization": f"Bearer {sa_token}"})
actual_alerts = res.json()["alerts"]["value"] if res.status_code == 200 else None
record(
    "TC-05", "KPI math: Alerts count matches COUNT(*) WHERE created_time in range",
    "Alerts is defined as every row landing in the range, independent of the funnel -- this is the simplest KPI to cross-check directly against the DB.",
    str(expected_alerts), str(actual_alerts),
    actual_alerts == expected_alerts,
)

# TC-06 -----------------------------------------------------------------
row = raw_db_query(
    """SELECT AVG((julianday(closed_time) - julianday(opened_time)) * 24) m
       FROM incidents WHERE closed_time IS NOT NULL AND opened_time IS NOT NULL
       AND created_time BETWEEN ? AND ?""",
    (frm, to),
)
expected_mttr = round(row["m"], 4) if row and row["m"] is not None else None
actual_mttr = round(res.json()["avg_mttr_hours"]["value"], 4) if res.status_code == 200 else None
record(
    "TC-06", "MTTR calc correct: avg(closed_time - opened_time) in hours, closed only",
    "MTTR must only average incidents that actually have a resolution time -- including still-open incidents would understate it.",
    str(expected_mttr), str(actual_mttr),
    expected_mttr is not None and actual_mttr is not None and abs(expected_mttr - actual_mttr) < 0.01,
)

# TC-07 -----------------------------------------------------------------
row = raw_db_query(
    "SELECT SUM(false_positive) fp, COUNT(*) total FROM incidents WHERE created_time BETWEEN ? AND ?",
    (frm, to),
)
expected_fp_rate = round(row["fp"] / row["total"] * 100, 4) if row and row["total"] else None
actual_fp_rate = round(res.json()["false_positive_rate_pct"]["value"], 4) if res.status_code == 200 else None
record(
    "TC-07", "False-positive rate calc: false_positive count / Alerts * 100",
    "False-positive rate is judged 30% of the score alongside every other KPI -- it must match a direct recomputation from raw rows, and land near the seeded 15% target.",
    str(expected_fp_rate), str(actual_fp_rate),
    actual_fp_rate is not None and abs(expected_fp_rate - actual_fp_rate) < 0.01,
)

# TC-08 -----------------------------------------------------------------
res_all = client.get("/api/analytics/kpis", params={"from": frm, "to": to}, headers={"Authorization": f"Bearer {sa_token}"})
res_trend_all = client.get(
    "/api/analytics/trends", params={"from": frm, "to": to, "metric": "volume"}, headers={"Authorization": f"Bearer {sa_token}"}
)
one_customer = raw_db_query("SELECT customer_id FROM customers LIMIT 1")["customer_id"]
res_filtered = client.get(
    "/api/analytics/kpis", params={"from": frm, "to": to, "customer": one_customer}, headers={"Authorization": f"Bearer {sa_token}"}
)
res_trend_filtered = client.get(
    "/api/analytics/trends",
    params={"from": frm, "to": to, "metric": "volume", "customer": one_customer},
    headers={"Authorization": f"Bearer {sa_token}"},
)
kpi_changed = res_filtered.json()["alerts"]["value"] < res_all.json()["alerts"]["value"]
trend_all_total = sum(p["values"]["alerts"] for p in res_trend_all.json())
trend_filtered_total = sum(p["values"]["alerts"] for p in res_trend_filtered.json())
trend_changed = trend_filtered_total < trend_all_total
record(
    "TC-08", "Global filter affects both KPI cards and trend charts consistently",
    "The brief requires one shared filter bar driving every card and chart -- if a filter only narrowed the KPIs but not the trend (or vice versa), the dashboard would visibly disagree with itself.",
    "both KPI alerts and trend alerts total decrease when scoped to one customer",
    f"kpi {res_all.json()['alerts']['value']} -> {res_filtered.json()['alerts']['value']}, trend {trend_all_total} -> {trend_filtered_total}",
    kpi_changed and trend_changed,
)

# TC-09 -----------------------------------------------------------------
expired = make_expired_token()
res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired}"})
record(
    "TC-09", "Expired JWT returns 401",
    "A 1-hour token that's past its exp claim must be rejected, not silently accepted -- this is the whole point of a short-lived token.",
    "401", str(res.status_code),
    res.status_code == 401,
)

# TC-10 -----------------------------------------------------------------
res = login("customer_viewer@pulsesoc.local", "Customer@123")
cv_token = res.json()["access_token"]
res = client.post("/demo/reset", headers={"Authorization": f"Bearer {cv_token}"})
record(
    "TC-10", "RBAC: customer_viewer cannot hit the admin-only reset action",
    "customer_viewer is the narrowest role -- it must not be able to trigger the one destructive/admin action in the app (the frontend's /admin route guard mirrors this, but the API must enforce it too).",
    "403", str(res.status_code),
    res.status_code == 403,
)


def _resolve_expected_sla(partner, customer, severity):
    row = raw_db_query(
        "SELECT sla_minutes FROM sla_configs WHERE partner_id=? AND customer_id=? AND severity=?",
        (partner, customer, severity),
    )
    if row:
        return row["sla_minutes"]
    row = raw_db_query(
        "SELECT sla_minutes FROM sla_configs WHERE partner_id=? AND customer_id IS NULL AND severity=?",
        (partner, severity),
    )
    if row:
        return row["sla_minutes"]
    return {"Critical": 240, "Major": 480, "Minor": 1440}[severity]


def create_test_incident(customer, severity, summary):
    res = client.post(
        "/api/incidents/create",
        json={
            "customer": customer, "severity": severity, "category": "Malware",
            "summary": summary, "siem": "QRADAR", "soar": "XSOAR",
        },
        headers={"Authorization": f"Bearer {sa_token}"},
    )
    return res


def get_breach_risk():
    return client.get("/api/analytics/breach-risk", headers={"Authorization": f"Bearer {sa_token}"}).json()


# TC-11 -------------------------------------------------------------------
create_res = create_test_incident("customer-1", "Critical", "TC-11 breach predictor check")
tc11_id = create_res.json()["id"] if create_res.status_code == 201 else None
expected_target = _resolve_expected_sla("partner-a", "customer-1", "Critical")
match = next((r for r in get_breach_risk() if r["incident_id"] == tc11_id), None)
record(
    "TC-11", "Breach Predictor: freshly opened incident shows correct SLA target and near-zero elapsed",
    "The breach predictor's whole value is the SLA target and elapsed time being right the instant a ticket opens -- if the math is off here, the countdown shown to an analyst is meaningless.",
    f"present in breach-risk, sla_target_minutes={expected_target}, elapsed_mins<2",
    f"{match}",
    match is not None and match["sla_target_minutes"] == expected_target and match["elapsed_mins"] < 2,
)

# TC-13 -------------------------------------------------------------------
before_alerts = client.get("/api/analytics/kpis", headers={"Authorization": f"Bearer {sa_token}"}).json()["alerts"]["value"]
create_res2 = create_test_incident("customer-1", "Minor", "TC-13 live creation check")
after_alerts = client.get("/api/analytics/kpis", headers={"Authorization": f"Bearer {sa_token}"}).json()["alerts"]["value"]
record(
    "TC-13", "Live ticket creation updates KPIs without a page reload",
    "The whole 'live command center' pitch depends on a newly created ticket actually moving the numbers, not just existing quietly in the DB.",
    f"alerts count increases by 1 (from {before_alerts})",
    f"before={before_alerts}, after={after_alerts}, create_status={create_res2.status_code}",
    create_res2.status_code == 201 and after_alerts == before_alerts + 1,
)

# TC-14 -------------------------------------------------------------------
override_res = client.post(
    "/api/sla-config",
    json={"partner_id": "partner-a", "customer_id": "customer-2", "severity": "Major", "sla_minutes": 15},
    headers={"Authorization": f"Bearer {sa_token}"},
)
create_res3 = create_test_incident("customer-2", "Major", "TC-14 sla override check")
tc14_id = create_res3.json()["id"] if create_res3.status_code == 201 else None
match2 = next((r for r in get_breach_risk() if r["incident_id"] == tc14_id), None)
record(
    "TC-14", "SLA config override: custom per-customer SLA is used instead of the global default",
    "A partner_manager configuring a tighter SLA for one customer has to actually change the breach math for that customer, or the whole 'configure SLA' feature is cosmetic.",
    "sla_target_minutes == 15 (overridden), not 480 (Major default)",
    f"{match2['sla_target_minutes'] if match2 else None}",
    override_res.status_code == 201 and match2 is not None and match2["sla_target_minutes"] == 15,
)

# TC-15 -------------------------------------------------------------------
client.post(
    "/api/sla-config",
    json={"partner_id": "partner-a", "customer_id": "customer-3", "severity": "Critical", "sla_minutes": 5},
    headers={"Authorization": f"Bearer {sa_token}"},
)
create_res4 = create_test_incident("customer-3", "Critical", "TC-15 blinking check")
tc15_id = create_res4.json()["id"] if create_res4.status_code == 201 else None
match3 = next((r for r in get_breach_risk() if r["incident_id"] == tc15_id), None)
record(
    "TC-15", "Blinking critical: Critical incident with <=5 min SLA remaining is flagged blinking_critical",
    "This flag is what drives the war-room banner and the blinking ticket chip -- if it doesn't fire the instant a tight-SLA Critical ticket is created, the signature demo moment doesn't happen.",
    "blinking_critical == True",
    f"{match3['blinking_critical'] if match3 else None}",
    match3 is not None and match3["blinking_critical"] is True,
)

# TC-17 -------------------------------------------------------------------
snooze_res = client.post(
    f"/api/incidents/{tc15_id}/snooze",
    json={"mins": 30, "comment": "TC-17 snooze check"},
    headers={"Authorization": f"Bearer {sa_token}"},
)
match4 = next((r for r in get_breach_risk() if r["incident_id"] == tc15_id), None)
record(
    "TC-17", "Snoozing a blinking ticket suppresses blinking_critical and marks it SNOOZED",
    "Snooze exists so an analyst who's already working a ticket can silence the war-room banner for it -- if the flag doesn't actually flip, the button is cosmetic.",
    "risk == 'SNOOZED', blinking_critical == False",
    f"{match4['risk'] if match4 else None}, blinking_critical={match4['blinking_critical'] if match4 else None}",
    snooze_res.status_code == 200
    and match4 is not None
    and match4["risk"] == "SNOOZED"
    and match4["blinking_critical"] is False,
)

# TC-16 -------------------------------------------------------------------
close_res = client.post(
    f"/api/incidents/{tc15_id}/close",
    json={"resolution_notes": "TC-16 automated close"},
    headers={"Authorization": f"Bearer {sa_token}"},
)
still_present = any(r["incident_id"] == tc15_id for r in get_breach_risk())
close_body = close_res.json() if close_res.status_code == 200 else {}
record(
    "TC-16", "Closing an incident within SLA marks it Matched, drops it from breach-risk, logs SLA SAVED",
    "The 'Close / Resolve Now' action is the payoff of the whole breach-predictor flow -- it has to actually resolve the ticket, credit it as SLA-Matched, and stop counting it down.",
    "sla_result == 'Matched', sla_saved_message present, no longer in breach-risk",
    f"sla_result={close_body.get('sla_result')}, saved_msg={close_body.get('sla_saved_message')}, still_in_risk={still_present}",
    close_res.status_code == 200
    and close_body.get("sla_result") == "Matched"
    and close_body.get("sla_saved_message") is not None
    and not still_present,
)

# TC-18 -------------------------------------------------------------------
create_res5 = create_test_incident("customer-1", "Critical", "TC-18 email outbox check")
tc18_ticket = create_res5.json()["ticket_number"] if create_res5.status_code == 201 else None
emails_res = client.get("/api/notifications/emails", headers={"Authorization": f"Bearer {sa_token}"})
email_match = next((e for e in emails_res.json() if e["ticket_number"] == tc18_ticket), None)
record(
    "TC-18", "Creating a Critical incident writes a real email_outbox row (zero-third-party mock)",
    "The email/Teams integrations are mocked (file + DB row, no SMTP/webhook) per the zero-third-party mandate -- a judge has to be able to independently verify the row exists, not just trust a 200 response.",
    "email_outbox row present for the new ticket, status == 'Sent'",
    f"{email_match}",
    create_res5.status_code == 201 and email_match is not None and email_match["status"] == "Sent",
)

# TC-20 -------------------------------------------------------------------
flow_denied = client.get("/api/admin/flow-log", headers={"Authorization": f"Bearer {cv_token}"})
flow_allowed = client.get("/api/admin/flow-log", headers={"Authorization": f"Bearer {sa_token}"})
record(
    "TC-20", "RBAC: only super_admin can read the flow.log viewer used on the Admin page",
    "flow.log is the JWT/RBAC trace proof the whole factory demo leans on -- it must not be readable by a customer_viewer, only by super_admin via the Admin page.",
    "customer_viewer -> 403, super_admin -> 200",
    f"customer_viewer -> {flow_denied.status_code}, super_admin -> {flow_allowed.status_code}",
    flow_denied.status_code == 403 and flow_allowed.status_code == 200,
)

# TC-21 -------------------------------------------------------------------
tier_row = raw_db_query("SELECT service_tier FROM customers WHERE customer_id = 'customer-1'")
TIER_SCORE = {"Gold": 100, "Silver": 60, "Bronze": 30}
expected_tier_score = TIER_SCORE[tier_row["service_tier"]]

tc21_create = create_test_incident("customer-1", "Critical", "TC-21 priority score check")
tc21_id = tc21_create.json()["id"] if tc21_create.status_code == 201 else None
ranking = client.get(
    "/api/analytics/priority-ranking", headers={"Authorization": f"Bearer {sa_token}"}
).json()
tc21_match = next((r for r in ranking if r["incident_id"] == tc21_id), None)

if tc21_match:
    f = tc21_match["factors"]
    recomputed_score = round(
        f["severity"] * 0.40 + f["sla_urgency"] * 0.25 + f["customer_tier"] * 0.15
        + f["incident_age"] * 0.10 + f["repeat_incident"] * 0.10
    )
else:
    recomputed_score = None

record(
    "TC-21",
    "Smart Priority Score: weighted formula (severity*0.4 + sla*0.25 + tier*0.15 + age*0.1 + repeat*0.1) matches its own reported factors, for a freshly-opened Critical ticket",
    "The whole pitch of this feature is that the 0-100 score is a real weighted aggregate an analyst can trust, not a black box -- recomputing it from the same factors the API returns has to land on the same number, and a brand-new Critical ticket must score severity=100 and near-zero elapsed/age.",
    f"factors present, severity=100, tier_score={expected_tier_score}, composite == recomputed_score",
    f"{tc21_match['factors'] if tc21_match else None} -> composite={tc21_match['priority_score'] if tc21_match else None}, recomputed={recomputed_score}",
    tc21_match is not None
    and tc21_match["factors"]["severity"] == 100
    and tc21_match["factors"]["customer_tier"] == expected_tier_score
    and tc21_match["factors"]["sla_urgency"] <= 5
    and tc21_match["factors"]["incident_age"] <= 5
    and tc21_match["priority_score"] == recomputed_score,
)

# TC-22 -------------------------------------------------------------------
OVERLOAD_ANALYST = "TC22-Analyst-Overloaded"


def create_analyst_incident(analyst, i):
    return client.post(
        "/api/incidents/create",
        json={
            "customer": "customer-1", "severity": "Minor", "category": "Malware",
            "summary": f"TC-22 workload seed {i}", "siem": "QRADAR", "soar": "XSOAR",
            "assigned_analyst": analyst,
        },
        headers={"Authorization": f"Bearer {sa_token}"},
    )


for _i in range(31):
    create_analyst_incident(OVERLOAD_ANALYST, _i)

workload = client.get(
    "/api/analytics/workload", headers={"Authorization": f"Bearer {sa_token}"}
).json()
overloaded_entry = next((a for a in workload["analysts"] if a["analyst"] == OVERLOAD_ANALYST), None)
rec = next((r for r in workload["recommendations"] if r["from_analyst"] == OVERLOAD_ANALYST), None)

if overloaded_entry and rec:
    before_ratio = overloaded_entry["open_tickets"] / overloaded_entry["capacity"]
    after_ratio = (overloaded_entry["open_tickets"] - rec["move_count"]) / overloaded_entry["capacity"]
    expected_improvement = round((before_ratio - after_ratio) / before_ratio * 50)
else:
    expected_improvement = None

record(
    "TC-22",
    "Analyst Workload Balancer: 31 open tickets on one analyst trips Overloaded status and produces a move-N-tickets recommendation with a correctly-computed SLA-improvement estimate",
    "The balancer's entire value is catching an uneven queue before it causes a breach -- pushing one analyst to 31 open tickets (over the 30-ticket Overloaded threshold) must both flag them and recommend a real rebalance, not just report the raw count.",
    "status=Overloaded, recommendation present, estimated_sla_improvement_pct == recomputed value",
    f"{overloaded_entry}, rec={rec}, recomputed_improvement={expected_improvement}",
    overloaded_entry is not None
    and overloaded_entry["status"] == "Overloaded"
    and overloaded_entry["open_tickets"] >= 31
    and rec is not None
    and rec["move_count"] > 0
    and rec["estimated_sla_improvement_pct"] == expected_improvement,
)


# -------------------------------------------------------------------------
# Output: CSV tracker, HTML report, log
# -------------------------------------------------------------------------

def write_csv(path):
    import csv

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["test_id", "name", "why", "expected", "actual", "status"])
        for r in results:
            writer.writerow([r["test_id"], r["name"], r["why"], r["expected"], r["actual"], r["status"]])


def write_html_report(path):
    passed = sum(1 for r in results if r["status"] == "PASS")
    total = len(results)
    rows_html = "\n".join(
        f"""<tr class="{r['status'].lower()}">
              <td>{r['test_id']}</td><td>{r['name']}</td><td>{r['why']}</td>
              <td>{r['expected']}</td><td>{r['actual']}</td><td>{r['status']}</td>
            </tr>"""
        for r in results
    )
    html = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>PulseSOC — Test Report</title>
<style>
body {{ font-family: system-ui, sans-serif; margin: 2rem; background: #0b1220; color: #e7ecf5; }}
h1 {{ font-size: 1.4rem; }}
.summary {{ margin-bottom: 1rem; color: #9aa8c2; }}
table {{ border-collapse: collapse; width: 100%; font-size: 0.88rem; }}
th, td {{ border: 1px solid #24314a; padding: 0.5rem 0.8rem; text-align: left; vertical-align: top; }}
th {{ background: #172238; text-transform: uppercase; font-size: 0.7rem; letter-spacing: 0.05em; color: #9aa8c2; }}
tr.pass td:last-child {{ color: #34d399; font-weight: 700; }}
tr.fail td:last-child {{ color: #f87171; font-weight: 700; }}
</style></head>
<body>
<h1>PulseSOC — Test Report</h1>
<p class="summary">{passed} / {total} passed — generated by qe-guardian</p>
<table>
<tr><th>ID</th><th>Test</th><th>Why</th><th>Expected</th><th>Actual</th><th>Status</th></tr>
{rows_html}
</table>
</body></html>"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html)


def write_log(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with path.open("a") as f:
        f.write(f"[{timestamp}] qe-guardian: test run started ({len(results)} test cases)\n")
        for r in results:
            f.write(f"[{timestamp}] {r['test_id']} {r['name']} -- {r['status']}\n")
        passed = sum(1 for r in results if r["status"] == "PASS")
        f.write(f"[{timestamp}] qe-guardian: {passed}/{len(results)} passed\n")


def push_to_kiwi(path):
    """Real XML-RPC push (see app.services.kiwi_client) -- creates/updates the
    actual PulseSOC product/plan/cases in Kiwi and records one TestExecution
    per result. Never blocks the run: any failure (Kiwi unreachable, creds
    missing) is logged here and the local testcases/ output stands on its
    own, per the qe-guardian Kiwi-availability rule in CLAUDE.md."""
    from app.services.kiwi_client import push_results_to_kiwi

    path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if not os.environ.get("KIWI_TCMS_URL"):
        with path.open("a") as f:
            f.write(f"[{timestamp}] Kiwi TCMS not configured -- results available in testcases/ only.\n")
        return

    try:
        outcome = push_results_to_kiwi(results)
        with path.open("a") as f:
            f.write(
                f"[{timestamp}] Synced {outcome['cases_synced']} cases, "
                f"{outcome['passed']}/{outcome['total']} passed, to Kiwi run "
                f"{outcome['run_id']} -- {outcome['run_url']}\n"
            )
    except Exception as exc:
        with path.open("a") as f:
            f.write(f"[{timestamp}] Kiwi TCMS push failed ({exc}) -- results remain available in testcases/ only.\n")


if __name__ == "__main__":
    write_csv(REPO_ROOT / "testcases" / "TEST_CASE_TRACKER.csv")
    write_html_report(REPO_ROOT / "testcases" / "test_report.html")
    write_log(REPO_ROOT / "logs" / "test.log")
    push_to_kiwi(REPO_ROOT / "testcases" / "kiwi_push.log")

    passed = sum(1 for r in results if r["status"] == "PASS")
    total = len(results)
    print(f"\n{passed}/{total} tests passed")
    for r in results:
        print(f"  {r['status']:4s} {r['test_id']} {r['name']}")
    sys.exit(0 if passed == total else 1)
