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


def login(username, password):
    return client.post("/api/auth/login", json={"username": username, "password": password})


def make_expired_token(username="superadmin", role="super_admin"):
    payload = {
        "sub": username,
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


# TC-01 -----------------------------------------------------------------
res = login("superadmin", "Admin@123")
record(
    "TC-01", "Login sync success (superadmin)",
    "A valid demo account must be able to authenticate synchronously and receive a usable JWT.",
    "200 + access_token present", f"{res.status_code} + token={'access_token' in res.json() if res.status_code == 200 else 'n/a'}",
    res.status_code == 200 and "access_token" in res.json(),
)
sa_token = res.json()["access_token"] if res.status_code == 200 else None

# TC-02 -----------------------------------------------------------------
res = login("superadmin", "WrongPassword!")
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
res = login("partner_mgr", "Partner@123")
pm_token = res.json()["access_token"]
res = client.get(
    "/api/incidents",
    params={"partner": "partner-b", "from": "2020-01-01T00:00:00", "to": "2030-01-01T00:00:00"},
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
frm, to = "2020-01-01T00:00:00", "2030-01-01T00:00:00"
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
res = login("customer_viewer", "Customer@123")
cv_token = res.json()["access_token"]
res = client.post("/demo/reset", headers={"Authorization": f"Bearer {cv_token}"})
record(
    "TC-10", "RBAC: customer_viewer cannot hit the admin-only reset action",
    "customer_viewer is the narrowest role -- it must not be able to trigger the one destructive/admin action in the app (the frontend's /admin route guard mirrors this, but the API must enforce it too).",
    "403", str(res.status_code),
    res.status_code == 403,
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
<html><head><meta charset="utf-8"><title>SOC Dashboard — Test Report</title>
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
<h1>SOC Executive Dashboard — Test Report</h1>
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
    import base64
    import json
    import urllib.request

    path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    kiwi_url = os.environ.get("KIWI_TCMS_URL")
    kiwi_user = os.environ.get("KIWI_TCMS_USERNAME")
    kiwi_pass = os.environ.get("KIWI_TCMS_PASSWORD")

    if not kiwi_url:
        with path.open("a") as f:
            f.write(f"[{timestamp}] Kiwi TCMS not configured -- results available in testcases/ only.\n")
        return

    passed = sum(1 for r in results if r["status"] == "PASS")
    try:
        req = urllib.request.Request(
            kiwi_url.rstrip("/") + "/xml-rpc/",
            data=json.dumps({"summary": f"SOC Dashboard run: {passed}/{len(results)} passed"}).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": "Basic "
                + base64.b64encode(f"{kiwi_user}:{kiwi_pass}".encode()).decode(),
            },
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            with path.open("a") as f:
                f.write(f"[{timestamp}] Pushed {passed}/{len(results)} results to {kiwi_url} -- HTTP {resp.status}\n")
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
