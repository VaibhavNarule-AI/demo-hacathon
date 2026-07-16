---
name: demo-storytelling
description: How to turn a working hackathon build into a rehearsed demo script and jury pitch. Use after feature freeze, once the build is stable - proactively, don't wait to be asked. This is a writing/structuring procedure, not investigative work, so it runs in the current context rather than as a separate agent.
---

Turn a working hackathon build into a performance, for a solo, non-developer presenter
who needs the material to be sayable out loud under mild pressure, not just written down.

## The job

1. Fill in `04_DEMO_SCRIPT_TEMPLATE.md`: the exact sequence of clicks/commands for the
   live demo, what to say while each step runs, and the single payoff moment the sequence
   should build toward.
2. Fill in `05_JURY_PITCH_TEMPLATE.md`: the 6-slide structure — problem, agent, live
   demo, impact/ROI, product viability/what's next, how AI was used to build it.
3. Pull concrete details from the actual build and tracker docs rather than inventing
   generic language — the impact numbers, the failure modes handled, and the "why it's
   an agent" framing should all trace back to real decisions made earlier in the day.

## Ground rules

- Open with the human problem, not the technology. Every draft opening line should name
  a persona and a concrete manual task, not "we built an AI solution that..."
- Keep slide text sparse — the presenter should be saying the detail, not reading it off
  a slide packed with text.
- Explicitly route the demo script around any fragile paths listed in
  `03_BUILD_TRACKER_TEMPLATE.md`'s known-issues table, or give the presenter a confident
  one-liner to say if a fragile path is unavoidable ("one thing I'd harden next is...").
- Include, explicitly, a line about how Claude Code / sub-agents were used to build this
  solo, and any multi-AI-tool cross-checking done (per the multi-AI differentiation
  guidance) — for an AI hackathon, the presenter's own use of AI is itself part of what's
  being judged, not just the artifact.
- Time-check the whole thing against the hard 5-minute limit (organizer-enforced, then a
  separate 5-minute Q&A) — budget roughly 2:30 for the live sequence per
  `05_JURY_PITCH_TEMPLATE.md`'s breakdown, and cut a step rather than asking the
  presenter to rush.
- End with impact stated in concrete (even if estimated) terms — never leave the ROI to
  be inferred by the jury.

## Output

Completed `04_DEMO_SCRIPT_TEMPLATE.md` and `05_JURY_PITCH_TEMPLATE.md`, plus a short note
on which known issues (if any) the demo script deliberately avoids.
