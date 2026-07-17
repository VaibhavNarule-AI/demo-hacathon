# Product Viability — SOC Executive Dashboard

**Who would pay for / adopt this beyond the hackathon?**
The MSSP's own account managers (one dashboard per partner instead of manual weekly
reports) and, white-labeled, the partners' own customers who currently get a static
PDF report instead of a live view.

**What's the smallest next version beyond the demo?**
Swap the seed data for a real SecurityHub read replica (or a scheduled export job)
behind the same repository interface — `analytics_service.py` doesn't change, only
`DB_TYPE` and the repository implementation do.

**Biggest risk to it being real:**
KPI trust — if leadership's manual numbers ever disagree with the dashboard's, the
tool dies on day one. That's why every formula is documented as an explicit
assumption in `02_SOLUTION_ARCHITECTURE_TEMPLATE.md` rather than left implicit, and
why `test_runner.py` cross-checks each one directly against raw SQL rather than only
asserting against itself.

**What would need to be rebuilt vs. what survives from the hackathon build:**
Survives: the RBAC/tenant-scoping model, the KPI formulas and their documented
assumptions, the filter-bar-drives-everything UI pattern, the logical service
boundaries. Rebuilt: the storage layer (SQLite → Postgres/Mongo), real SIEM/SOAR
ingestion in place of `seed.py`, and splitting the one FastAPI process into the four
containers it was already logically organized around.
