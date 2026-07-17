---
name: engineering-principles
description: Operating principles for rapid builds — time-boxing, scope discipline, and what to cut vs keep under a deadline. Load before starting a new use case.
---

# Engineering Principles

- **Working demo beats a complete feature set.** Build the one flow a judge will
  click through, end to end, before touching anything else.
- **Time-box every step.** If architecture takes longer than the build, the scope
  was too big — cut it.
- **Auth is not optional scope.** JWT + RBAC is table stakes for this factory; don't
  build a demo without it, but don't gold-plate it either (1h expiry, bcrypt,
  `require_role` — no more).
- **Visible progress beats silent progress.** Console logs, `/health`, `/flow` —
  judges and teammates should see the system working, not just trust that it does.
- **Logs and tests are the proof, not the narration.** `logs/` proves work was done;
  `testcases/` proves it's correct. Don't skip either to save time — they're what
  makes the demo credible.
- **When in doubt, cut scope, not quality.** A smaller flow that's fully
  authenticated and tested beats a bigger one that isn't.
