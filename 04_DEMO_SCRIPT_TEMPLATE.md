# Demo Script — SOC Executive Dashboard

_See the `presentation-standards` skill before filling this in._

**Problem, in one sentence:**
An MSSP SOC serving many customers has no single place to see alert volume,
detection/response speed, SLA compliance, or noise — the data's all in SecurityHub,
it just isn't surfaced.

**Persona walked through the demo:** A SOC leader checking this week's posture
across their partners, then a partner/customer checking their own scope.

**Flow (step by step, what you click/say):**
1. Open http://localhost:8000, log in as `superadmin` / `Admin@123`. Say: "This is
   the whole SOC, every partner." Point at the 9 KPI cards and the WoW deltas.
2. Change the global filter bar — pick one customer, one SIEM. Watch every KPI card
   *and* both trend charts update together off the same filter state. If the
   amber "P1 at risk" banner is showing, point at it — a Critical incident open
   3+ hours, flagged before it crosses the 4h SLA breach threshold.
3. Click an incident row in the table — drill-down modal opens: MITRE technique,
   assigned analyst, recommendation.
4. Log out, log back in as `partner_mgr` / `Partner@123`. Say: "Same dashboard, but
   this is a partner manager — watch the data narrow." Show the customer dropdown
   only lists partner-a's customers.
5. Log out, log back in as `customer_viewer` / `Customer@123`. Say: "And this is
   what their own customer sees — one customer's data only, no partner picker."
6. **The hard part, live:** as `customer_viewer`, try to hit `/admin` directly in
   the URL bar → redirected to the unauthorized page. Then show the same 403
   happening at the API layer via `/flow`.
7. Pull up `/health`, `/flow`, and `/test-report` in three tabs — proof the system
   is live, the RBAC flow is real, and the tests actually ran.

**Hard part to show live (e.g. a 403 happening):** Step 6 above — a wrong-role
direct-URL attempt getting blocked both client-side (redirect) and server-side (403
in `/flow`). This is deliberately the moment that lands hardest with judges.

**Backup if the live API breaks:** Skip straight to `/test-report`
(`testcases/test_report.html`) — it's a static, already-generated page showing all
10 test cases (including the tenant-isolation and KPI-math ones) passing, so the
correctness claim still stands even if the live demo has a network hiccup.

**Proof to pull up:** `/health` · `/flow` · `testcases/test_report.html` · the Kiwi
TCMS run at `https://dev.securityhub365.com/kiwi/runs/search/`

**Closing line (impact beyond the hackathon):** Same factory, same agents, same
JWT+RBAC discipline — the next use case gets built the same way, not from scratch.
