---
name: qe-testing-checklist
description: The concrete adversarial-testing checklist for a hackathon demo - what to try, in what order, and what counts as a floor (not a full test suite). Invoked by the qe-guardian agent, or directly in the main thread for a quick check without spinning up a separate agent.
---

This is the "how to test" methodology - separate from the `qe-guardian` agent, which is
the "who runs it in isolation" worker. Use this skill directly (no agent needed) for a
quick single check; use the `qe-guardian` agent when you want a fuller isolated pass that
keeps a lot of tool output out of the main thread.

## The checklist, in order

1. Run the exact demo sequence as scripted, twice in a row, back to back — many bugs
   only show up on the second run (stale state, leftover files, cached output).
2. Try empty/blank input, obviously malformed input, and unexpected ordering of actions.
3. Try the exact input planned for the live demo, verbatim, at least twice.
4. Note anything that produces a raw stack trace, unhandled exception, or unreadable
   output — that specifically must not appear in front of a judge.

## Scope discipline

- Not trying to achieve full test coverage — there's a fixed, short time budget. Spend it
  on what's reachable from the actual demo path, not theoretical edge cases elsewhere in
  the code.
- Fix anything found quickly if proportionate to time remaining; otherwise record it in
  `03_BUILD_TRACKER_TEMPLATE.md`'s known-issues table with a concrete demo-time
  workaround (avoid that path live, or narrate around it confidently).
- Never let "we didn't have time to test it" be the reason something breaks live.

## Logging

Per `15_DEMO_RUNTIME_AND_TCMS_FLOW.md` §2: if a reachable Kiwi TCMS instance exists
(check this during design, not now), log results there via `tcms-api` instead of the
CSV. Otherwise log each test actually run as a row in `TEST_CASE_TRACKER_TEMPLATE.csv`
(test type, steps, expected/actual, pass/fail). Either way, this makes "we tested this
properly" a concrete, inspectable artifact instead of just a claim in the pitch.

Also confirm, as part of this pass: the whole product comes up from a single
run command with no manual setup steps (`15_DEMO_RUNTIME_AND_TCMS_FLOW.md` §3) — that's
what "run the exact demo sequence twice in a row" should actually be testing.
