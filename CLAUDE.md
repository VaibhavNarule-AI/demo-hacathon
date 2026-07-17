# Hackathon Factory — Operating Rules

## Purpose
This repo is a reusable **factory**, not a project. It holds agents, skills, and blank
templates only. Business logic for a specific use case is built fresh into `backend/`,
`frontend/`, `k8s/`, `devops/` each time — never into the framework files themselves.

## Agent Roster
| Agent | Responsibility | Writes |
|---|---|---|
| `solution-architect` | Designs `02_SOLUTION_ARCHITECTURE_TEMPLATE.md` — WHY + 3 diagrams (user journey, system architecture, RBAC flow) | `/logs/architect.log` |
| `rapid-builder` | Builds backend + frontend, JWT + RBAC included, visible `console.log` Step 1/2/3 | `/logs/build.log` |
| `code-reviewer` | Reviews for auth/RBAC bypass and security issues | `/logs/review.log` |
| `qe-guardian` | Runs tests, verifies the flow end to end, pushes to Kiwi TCMS | `/testcases/test_report.html`, `/logs/test.log`, `/testcases/kiwi_push.log` |

## Logging Rules
- All agents write logs to `/logs/`, not console-only. Never write logs to `docs/`.
- `rapid-builder` writes `/logs/build.log` after build — success/fail per file.
- `qe-guardian` writes `/testcases/test_report.html` + `/logs/test.log` after testing,
  pushes to Kiwi TCMS, and writes `/testcases/kiwi_push.log`.
- `code-reviewer` writes `/logs/review.log`.
- `solution-architect` writes `/logs/architect.log`.
- `/logs/flow.log` is written by the running application itself, not an agent —
  `rapid-builder` wires the backend so every request through the JWT/RBAC flow
  (login → token issued → protected route hit → RBAC filter applied) appends one
  trace line here. This is what the `/flow` demo endpoint reads from.
- `logs/` proves the work was done. `testcases/` proves it's correct. GitHub proves it
  was delivered.

## Git Flow
Remote is already configured: `origin -> https://github.com/VaibhavNarule-AI/demo-hacathon.git`
on branch `main`.

Only after `qe-guardian` passes and `/health` returns OK:
```
git add .
git commit -m "feat: working app with JWT RBAC"
git push -u origin main
```
Never push before QE signs off.

## External Integrations
- **GitHub** — `origin` is set to the repo above. First push needs `-u origin main`
  (already reflected in the command above); after that, plain `git push` works.
- **Kiwi TCMS** — configured. `qe-guardian` reads `KIWI_TCMS_URL`,
  `KIWI_TCMS_USERNAME`, `KIWI_TCMS_PASSWORD` from the local, gitignored `.env` (never
  commit or paste these into chat/logs) and pushes each test run there after
  populating `testcases/`. Judges can view runs live at
  `https://dev.securityhub365.com/kiwi/runs/search/` — add this alongside `/health`,
  `/flow`, and `test_report.html` in the demo (step 8 below). If Kiwi is ever
  unreachable at push time, `qe-guardian` logs the failure in
  `testcases/kiwi_push.log` rather than blocking the run — see the agent's Kiwi
  availability rules.

## Framework Discipline
- No business logic in the framework — only templates. Use-case code lives in
  `backend/`, `frontend/`, `k8s/`, `devops/`, `docs/`.
- One agent works at a time — no parallel agent runs, to keep token spend predictable.
- Max 500 lines per agent output. If a task needs more, split it into steps.

## JWT + RBAC Rules
**Backend**
- JWT access tokens expire in 1 hour (`exp` claim, 1h).
- Passwords hashed with bcrypt — never store plaintext.
- Role-gated routes use a `require_role` decorator.
- Unauthenticated → 401. Authenticated but wrong role → 403.

**Frontend**
- `ProtectedRoute` checks token presence + expiry from `localStorage` before rendering.
- Direct URL navigation to a protected route without a valid token redirects to login —
  no client-side-only bypass.
- All API calls attach the JWT as `Authorization: Bearer <token>` via an axios
  interceptor.
- A 401 response anywhere triggers auto-logout (clear token, redirect to login).

**End-to-end flow**
```
Login UI -> POST /login -> JWT issued -> GET /tasks with Bearer header
   -> RBAC filter server-side -> UI renders per-role view
```

**If the use case has no distinct roles**
JWT auth is still built — almost every real app needs to know who's logged in, even
with one role. RBAC is the part that scales down, not auth itself:
- `solution-architect` checks `01_PROBLEM_INTAKE_TEMPLATE.md`'s "Roles involved"
  field. One role (or none named) → the architecture doc states
  `RBAC: not applicable — single-role app` instead of drawing an empty RBAC flow
  diagram, and still draws the other two (user journey, system architecture).
- `rapid-builder` still builds login, JWT issuance, 1h expiry, bcrypt, and
  `ProtectedRoute` — those protect the app regardless of role count. It skips
  `require_role` / per-route role checks only when there's truly one role to check
  against.
- `code-reviewer` still checks auth bypass (missing token checks, expiry not
  enforced); the RBAC-specific checks (wrong-role → 403) are marked N/A rather than
  faked.
- `qe-guardian` still runs the full auth test matrix; the RBAC rows in
  `TEST_CASE_TRACKER.csv` are marked N/A instead of invented.
- Everything else — logging, `testcases/`, Kiwi push, UI quality bar, deploy, git
  flow, the demo proof set — applies exactly the same either way. The factory's
  value was never just RBAC; it's the same build → review → test → deploy → prove
  pipeline for any use case.

## UI Quality Bar
The demo is judged on sight before it's judged on code. `rapid-builder` never ships
a raw/unstyled screen — every screen it builds must look like a real product, not a
prototype:
- Consistent design system: one font pair, one color palette (primary + neutral +
  success/error), one spacing scale — reused across every screen, not invented per
  page.
- A real layout: header/nav, content area with proper padding and alignment, clear
  visual hierarchy (headline weight/size distinct from body text). No default
  browser-styled forms or buttons.
- States are designed, not skipped: loading, empty, error, and the 401/403 screens
  all get the same visual polish as the happy path — a judge will hit these.
- Responsive at demo size (laptop + projector) at minimum; mobile polish is a bonus,
  not a requirement.
- Bar to hit: a landing/demo screen should look closer to a polished marketing site
  (clean hero, aligned grid, consistent cards) than to an unstyled internal tool.

## Use-Case-to-Delivery Workflow
Run this whenever a new use case is given:
1. Fill `01_PROBLEM_INTAKE_TEMPLATE.md`.
2. `solution-architect` designs `02_SOLUTION_ARCHITECTURE_TEMPLATE.md` — WHY + 3
   diagrams (user journey, system architecture, RBAC flow).
3. `rapid-builder` builds backend/frontend with visible `console.log("Step 1: ...")`,
   `Step 2`, `Step 3` markers so the flow is traceable live.
4. `code-reviewer` checks for auth/RBAC bypass and other issues.
5. `qe-guardian` runs tests, stores results in `testcases/`, pushes to Kiwi TCMS.
6. Deploy locally via `docker-compose up`, then to k8s via `devops/deploy.sh`.
7. Git push (see Git Flow above).
8. Demo: show `/health`, `/flow`, `testcases/test_report.html`, and the live Kiwi
   TCMS run at `https://dev.securityhub365.com/kiwi/runs/search/`.
