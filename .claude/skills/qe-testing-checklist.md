---
name: qe-testing-checklist
description: Checklist qe-guardian follows when testing the JWT+RBAC flow before signing off on a build. Load before running tests.
---

# QE Testing Checklist

## Auth
- [ ] Login with correct credentials returns a JWT.
- [ ] Login with wrong credentials returns 401, not 500.
- [ ] Token expires at 1h — a request with an expired token returns 401.
- [ ] Passwords are bcrypt-hashed in storage, never plaintext.

## RBAC
- [ ] Each protected route enforces `require_role` server-side.
- [ ] A user with the wrong role gets 403, not a filtered empty result.
- [ ] A user with no token gets 401.
- [ ] Direct URL navigation to a protected frontend route without a valid token
      redirects to login.

## Flow
- [ ] Full flow works end to end: Login UI → POST /login → JWT → GET /tasks with
      Bearer → RBAC filter → UI.
- [ ] `/health` returns OK.
- [ ] `/flow` (or equivalent trace endpoint) reflects the actual request path.

## Reporting
- [ ] `testcases/TEST_CASE_TRACKER.csv` updated with this run's results.
- [ ] `testcases/USE_CASE_TRACKER.csv` updated.
- [ ] `testcases/test_report.html` regenerated.
- [ ] Results pushed to Kiwi TCMS; `testcases/kiwi_push.log` written either way
      (success or failure).
- [ ] `/logs/test.log` written with the full run.
