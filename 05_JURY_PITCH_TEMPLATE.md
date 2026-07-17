# Jury Pitch — PulseSOC (SOC Executive Command Center)

**One-sentence pitch:** A single-pane, multi-tenant dashboard that turns
PulseSOC's incident data into 9 correctly-computed KPIs, week-over-week trends,
and drill-down — scoped server-side by role, so a partner or customer only ever
sees their own slice.

**Why this matters (the problem):** Today leadership and customers have no single
place to see SOC performance. The data already exists in PulseSOC — it just
isn't surfaced, filtered, or trusted.

**What we built (not a feature list — the flow):** Login → JWT issued with tenant
claims → global filter bar drives every KPI card and both trend charts off one
shared state → drill into any incident for MITRE/analyst/recommendation context —
and the same flow narrows automatically depending on whether you're a super admin,
a partner manager, or a single customer's viewer.

**What makes it credible (proof, not promises):**
- `logs/` — every agent's log, proving the build actually happened
- `testcases/` — 10 test cases, including tenant isolation and KPI math
  cross-checked directly against raw SQL, not just asserted
- Kiwi TCMS — the same results pushed to an external system judges can open
  themselves
- GitHub — the commit history proves delivery, not just a local demo

**Anticipated questions:**
- Q: How does tenant isolation actually work — could a partner manager see another
  partner's data by editing the URL?
  A: No — `get_tenant_filter()` derives scope from the JWT claims only, and the
  repository layer always ANDs that scope into the SQL WHERE clause first. A
  conflicting `?partner=` query param is ignored, not honored. Verified live in the
  demo and covered by TC-04.

- Q: How is a false positive defined?
  A: An alert that never got opened — either because it was closed in under 15
  minutes without ever being triaged, or an analyst explicitly marked it. It's
  pre-computed at ingest time, not derived per-query, which is also why it cleanly
  falls out of the alert→incident funnel (a false positive never counts as an
  "incident").

- Q: How would this scale to 10,000 incidents a day?
  A: The KPI math runs in Python over rows fetched by a single indexed SQL query
  (indexes on `created_time`, `partner`, `customer`) — at 10k/day that's ~3.6M
  rows/year, well within SQLite's comfortable range for read-heavy analytics, and
  the `DB_TYPE` toggle means swapping to Postgres/Mongo for real concurrent write
  volume is a repository-layer change, not a rewrite of `analytics_service.py`.

- Q: How exactly is SLA calculated?
  A: Matched/Breached is only ever set once an incident is opened *and* closed
  (Breached specifically when it's P1/Critical and MTTR exceeds 4 hours);
  compliance % excludes never-opened incidents from the denominator entirely,
  because an SLA clock that never started can't be breached.

- Q: Why SQLite instead of Postgres?
  A: A 4-hour build judged on KPI correctness and RBAC, not infrastructure — SQLite
  is one file, trivial to seed/reset/back up, and the service layer never touches
  SQL directly outside the repository layer, so the migration path is real, just
  deliberately not spent time on today.

- Q: Isn't a 5-minute SLA unrealistic? Real Critical SLAs are hours, not minutes.
  A: Yes, deliberately — it's a demo setting, not a claim about real SOC practice.
  The point isn't the number, it's that SLA targets are configurable per partner and
  per customer at all (`sla_configs`, resolved customer-override → partner-default →
  global-default), and that the breach math actually uses whatever's configured
  instead of a hardcoded constant. A real deployment would set 4h/8h/24h and never
  touch it again.

- Q: How is the Customer Health Score weighted, and why those numbers?
  A: `100 − (breaches×12) − (fp_rate×0.6) − (avg_mttr_h×1.5)`, clamped 0–100 over a
  30-day window. Breaches are weighted heaviest because they're the thing a customer
  actually notices and escalates about; false-positive rate and MTTR matter but
  don't individually sink the score the way repeated breaches do. It's a starting
  point tuned against this seed data, not a universal constant — the formula lives
  in one function (`health_score.py`) specifically so it can be re-weighted per
  MSSP without touching anything else.
