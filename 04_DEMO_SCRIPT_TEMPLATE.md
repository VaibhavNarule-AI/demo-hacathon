# Demo Script — PulseSOC (SOC Executive Command Center)

_See the `presentation-standards` skill before filling this in._

**Problem, in one sentence:**
An MSSP SOC serving many customers has no single place to see alert volume,
detection/response speed, SLA compliance, or noise — the data's all in PulseSOC,
it just isn't surfaced.

**Persona walked through the demo:** A SOC leader checking this week's posture
across their partners, then a partner/customer checking their own scope, then a
live 60-second walkthrough of onboarding a new partner from scratch.

**Flow (step by step, what you click/say):**
1. Open http://localhost:8000, log in as `superadmin` / `Admin@123`. Say: "This is
   the whole SOC, every partner." Point at the 9 KPI cards (with sparklines) and
   the WoW deltas.
2. Change the global filter bar — multi-select two customers, pick a SIEM pill.
   Watch every KPI card *and* both trend charts update together off the same
   filter state. Point at the Early Warning System table above the KPIs — any
   ticket close to breaching shows a live countdown progress bar.
3. Click an incident row in the table — drill-down modal opens with the
   Event→Created→Opened→First Response→Closed timeline stepper, MITRE technique,
   assigned analyst, recommendation.
4. Click a bar on **Top Customers by Volume**. Say: "Every chart drills down —
   this jumps straight into Incidents pre-filtered to that customer."
5. **Live demo, no pre-baked data:** click **Demo Setup**. Walk the 4 steps live —
   register a new partner, onboard a customer, set a 5-minute Critical SLA, create
   a Critical ticket. The ticket appears **blinking red** in the Early Warning
   table immediately, and the War Room banner flashes at the top of the screen
   with a live countdown. Click **Close / Resolve Now** before it runs out — toast
   "SLA saved with N min left!", confetti, KPI cards update live.
6. Click **Command Center** — full-screen, dark, auto-refreshing every 10s, ticker
   scrolling recent activity. Say: "This is what's on the wall in the SOC." Press
   `Esc` to exit.
7. Log out, log back in as `partner_mgr` / `Partner@123`. Say: "Same dashboard, but
   this is a partner manager — watch the data narrow." Show the customer dropdown
   only lists partner-a's customers.
8. Log out, log back in as `customer_viewer` / `Customer@123`. Say: "And this is
   what their own customer sees — one customer's data only, no partner picker."
9. **The hard part, live:** as `customer_viewer`, try to hit `/admin` directly in
   the URL bar → redirected to the unauthorized page. Then show the same 403
   happening at the API layer via `/flow`.
10. Pull up `/health`, `/flow`, and `/test-report` in three tabs — proof the system
    is live, the RBAC flow is real, and the tests actually ran.

**Hard part to show live (e.g. a 403 happening):** Step 9 above — a wrong-role
direct-URL attempt getting blocked both client-side (redirect) and server-side (403
in `/flow`). Step 5's blinking-to-saved moment is the other one that lands hardest.

**Backup if the live API breaks:** Skip straight to `/test-report`
(`testcases/test_report.html`) — it's a static, already-generated page showing all
18 test cases (tenant isolation, KPI math, breach-predictor math, SLA overrides,
blinking detection, close-ticket SLA-saved) passing, so the correctness claim
still stands even if the live demo has a network hiccup.

**Proof to pull up:** `/health` · `/flow` · `testcases/test_report.html` · the Kiwi
TCMS run at `https://dev.securityhub365.com/kiwi/runs/search/`

**Closing line (impact beyond the hackathon):** Same factory, same agents, same
JWT+RBAC discipline — the next use case gets built the same way, not from scratch.
