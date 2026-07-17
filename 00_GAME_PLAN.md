# Game Plan

**Use case:** PulseSOC — SOC Executive Command Center (HACK-SOC-01) — multi-tenant MSSP single-pane
executive dashboard over PulseSOC incident data.
**Time budget:** 4–5 hours, single build session.

## Judging weights (assumed)
| Weight | Dimension |
|---|---|
| 30% | Correct KPI math — every formula in `02_SOLUTION_ARCHITECTURE_TEMPLATE.md` matches what the API actually returns |
| 20% | Filter behavior — one global filter bar drives every KPI card and both trend charts consistently |
| 20% | Usable single-pane design — a SOC leader reads status at a glance, no digging |
| 15% | Bonus creativity — SLA-breach early warning, drill-down depth, anything beyond the brief |
| 15% | Code quality — clean layering (core/models/repositories/services), tenant isolation actually enforced, tests passing |

Optimize for the 30+20+20 = 70% that's pure correctness and usability before spending
time on the 15% creativity bonus.

## Milestones
| Time | Milestone | Owner |
|---|---|---|
| T+0:00 | Problem intake filled, architecture decided | solution-architect |
| T+0:45 | DB schema + seed data generating 2,000 incidents | rapid-builder |
| T+1:30 | Backend API complete — auth, incidents, analytics, customers | rapid-builder |
| T+2:30 | Frontend complete — login, filter bar, KPI cards, trend charts, drill-down | rapid-builder |
| T+3:00 | Review complete — bypass/tenant-isolation check | code-reviewer |
| T+3:30 | Tests passing, testcases/ populated, Kiwi push attempted | qe-guardian |
| T+4:00 | Docker build green, `/health` live, k8s manifest applied | devops |
| T+4:20 | Git pushed | — |
| T+4:40 | Demo rehearsed end to end | — |

## Cut list (if time runs short)
- Cut first: the SLA-breach early-warning bonus feature (15% weight, stretch goal only)
- Cut second: k8s deploy — `docker-compose up` alone is enough to demo; k8s is the
  "sellable, not just a hackathon toy" proof, not the demo itself
- Never cut: KPI correctness, tenant isolation, the filter bar actually filtering
  everything — these are 70% of the score combined
