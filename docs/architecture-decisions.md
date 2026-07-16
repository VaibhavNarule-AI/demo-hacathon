# Architecture Decisions — the "why" log

This file holds the *reasoning* behind non-obvious decisions — not loaded into every
Claude session automatically, referenced only when someone (you, a teammate, a future
reader) needs to know why something is the way it is, not just what it is. Keeps
`CLAUDE.md` and the skill/agent files thin, since they only need the "what to do," not
the full debate behind it.

Add one entry per non-obvious decision, in this format:

```
## [Decision] — [date]

**Context:** what prompted this decision
**Decision:** what was chosen
**Why:** the reasoning, including alternatives considered and why they lost
**Revisit if:** what would change this decision
```

---

## Skills vs. agents split — 2026-07-16

**Context:** Needed a token-cost-optimized structure for the hackathon build, with a
clear rule for what's a Skill vs. what's an Agent, since the whole day's build
methodology runs through these rather than ad-hoc prompting.

**Decision:** Anything that's a reusable procedure/methodology with no independent
investigation to do (writing the demo script and pitch, the QE test checklist, the
core mindset/priorities) is a **Skill** — cheap when dormant (just a description line),
loaded into whichever context invokes it. Anything that does real bulky or investigative
work benefiting from an isolated context (architecture design, building, adversarial
testing, code review, compiling documentation from multiple source files) stays an
**Agent** — its tool calls and intermediate output stay out of the main thread, only the
result comes back.

**Why:** `demo-storyteller` and the QE checklist inside `qe-guardian` were pure "how to
do X" procedures with nothing to independently investigate — running them as full
separate agents spent a fresh context on work that didn't need isolation. Splitting the
checklist out of `qe-guardian` into its own skill also means it can be invoked directly
for a quick check without spinning up the full agent, when a fast look is all that's
needed.

**Revisit if:** a "skill" starts needing to read/investigate a lot on its own (that's a
sign it should be an agent instead), or an agent's job shrinks to pure writing with no
independent digging (that's a sign it should become a skill).
