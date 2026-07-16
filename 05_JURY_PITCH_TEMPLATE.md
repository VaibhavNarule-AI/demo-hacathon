# Jury Pitch — Interview Note Summarizer

6 slides, ~30 sec each outside the live demo slide, total ~5:00 including the ~2:30
live demo from `04_DEMO_SCRIPT_TEMPLATE.md`. Keep slide text sparse — say the detail,
don't put it on the slide.

---

## Slide 1 — The Problem

**Slide text (sparse):**
> After every interview, HR is left with raw notes and no consistent way to turn them
> into a decision.

**Say out loud:**
"Every interviewer takes notes their own way — different length, different focus,
different phrasing for the same thing. When it's time to decide, someone has to
re-read all of it and manually figure out: what's the strength, what's the concern,
what's the actual recommendation. That re-reading is where time gets lost, and where
two people reading the same notes can walk away with different conclusions."

---

## Slide 2 — The Agent

**Slide text (sparse):**
> Not a script. A judgment call, made consistently, every time.

**Say out loud:**
"A keyword script could flag words like 'communication' or 'leadership' — it can't
tell you someone was *hesitant* about leading a team when the notes never say that
directly. This agent reads the notes the way a person would: it infers what's only
implied, weighs conflicting signals — strong technical answers but a hesitant
tone about teamwork, say — into one overall judgment, and returns it in the same
structure every time: strengths, concerns, rating, recommendation. That consistency,
from messy human notes, is the part a script can't do."

---

## Slide 3 — Live Demo

*(No slide text — this is where you run `04_DEMO_SCRIPT_TEMPLATE.md`.)*

---

## Slide 4 — Impact / ROI

**Slide text (sparse):**
> ~10-15 minutes saved per interview, per candidate, on the summarization step alone.

**Say out loud:**
"If re-reading and writing up a summary of one candidate's notes takes ten to fifteen
minutes, and a hiring manager does this for every candidate in a pipeline, that adds
up fast across a hiring season — and it's not just time, it's consistency: the same
candidate's notes get judged the same way regardless of who's doing the summarizing
that day. This isn't replacing the hiring decision — it's removing the manual
re-reading step before that decision gets made."

---

## Slide 5 — Product Viability / What's Next

**Slide text (sparse):**
> Today: summarize one candidate's notes. Next: rank a shortlist, and answer questions
> across everyone's history.

**Say out loud:**
"What's built today is deliberately narrow — one candidate, one set of notes, one
structured summary — because that's the smallest piece that proves the core idea
works. The natural next steps, not built yet: ranking a full shortlist against each
other with reasoning, not just a score; and letting HR ask something like 'who scored
well on system design?' across everyone's stored history. Both reuse the exact same
storage and agent pattern already working here — this isn't a stretch, it's the same
architecture extended."

---

## Slide 6 — How AI Was Used to Build This

**Slide text (sparse):**
> Built solo, today, using Claude Code sub-agents for design, build, and adversarial
> testing — not just one long chat.

**Say out loud:**
"I'm a QE tester, not a developer, and this was built in one day using Claude Code.
Instead of one continuous conversation, the work was split across specialized
sub-agents: one for the architecture and stack decision, one for implementation in
two sprints, and — this is the part I'd call out specifically — a separate adversarial
QE pass, run the way I'd run a real test cycle: trying blank input, malformed input,
repeated runs, and checking that nothing showed a raw error to a user. That pass
actually caught and fixed a real bug — a confusing double error message when no API
key was configured — before I ever saw the app myself. And when deployment hit a wall
— company policy blocked the API key and the usual cloud hosting options — Claude Code
helped diagnose each failure directly from the actual error output and pivot to a
local Kubernetes setup with a public tunnel, rather than getting stuck. That
troubleshooting is part of the deliverable too, not just the app."
