# Hackathon Mode — instructions for Claude Code in this repo

This repo exists for one day: the Engineering AI Hackathon. Optimize everything for "a
working, demoable agent by presentation time," not for long-term maintainability.

## This is agentic/skill-based development, not prompt-based development

This is a structural rule, not a preference: for any nontrivial piece of work, check
whether it belongs to an existing skill (`.claude/skills/`) or agent (`.claude/agents/`)
per the table below, and use that mechanism — don't just answer conversationally in the
main thread from scratch as if this were an ad-hoc chat. If a new kind of work doesn't
fit any existing skill/agent, apply the decision rule in `13_SKILLS_VS_AGENTS_GUIDE.md`
to decide which one to add, rather than defaulting to freeform prompting because it's
faster in the moment. The main thread's job is orchestration — deciding what needs to
happen next and dispatching it — not doing every piece of work itself.

## Who you're working with

The user is a solo participant with a QE/testing background, not a software developer.
They will not always know the right technical vocabulary or the idiomatic way to do
something — infer intent from the business goal they describe and default to the
simplest working approach rather than asking them to specify implementation details they
may not have. Explain technical choices in plain terms when it affects a decision they
should weigh in on (e.g. tech stack, scope cuts); skip the explanation when it doesn't.

## Standing priorities (condensed — invoke the skill below for the full reasoning)

1. Solving the use case with AI beats writing good code — the jury never reads the code.
2. A running end-to-end demo beats more features.
3. Speed of iteration beats code quality — no refactors, no premature abstraction.
4. Review is functional + safety only (does it work, is it safe), never style.
5. Testing the demo path is not optional — run it live, twice, before presentation.
6. Explain decisions that affect the pitch; stay silent on ones that don't.
7. Notice reuse potential as you go — it costs nothing and it's what makes the
   product-viability pitch true rather than a stretch.

Invoke the **`hackathon-mindset`** skill (`.claude/skills/hackathon-mindset/SKILL.md`)
at the start of a session, or whenever a scope-cut or quality-tradeoff decision needs
the full reasoning behind these rather than just the rule. Don't re-derive this
reasoning from scratch each time — the skill exists so it doesn't have to sit fully
loaded in every context.

## Skills vs. agents in this repo

Naming convention: kebab-case, one skill = one directory under `.claude/skills/<name>/`
with a `SKILL.md` inside; one agent = one file under `.claude/agents/<name>.md`. Agent
names are role-nouns (`solution-architect`, `qe-guardian`); skill names are gerund/noun
phrases describing the procedure (`demo-storytelling`, `qe-testing-checklist`).

| Type | Name | What it's for |
|---|---|---|
| Skill | `hackathon-mindset` | The full priority reasoning, loaded on demand |
| Skill | `demo-storytelling` | Writing the demo script + pitch — pure procedure, no isolation needed |
| Skill | `qe-testing-checklist` | What to test and in what order — the methodology |
| Agent | `solution-architect` | Design work — isolated so exploration doesn't flood the main thread |
| Agent | `rapid-builder` | Implementation — isolated for the same reason |
| Agent | `qe-guardian` | Runs the `qe-testing-checklist` skill with isolated tool access |
| Agent | `code-reviewer` | Functional/safety review — isolated code reading |
| Agent | `docs-scribe` | Compiles documentation from multiple source files — isolated reading |

The reasoning behind this split lives in `docs/architecture-decisions.md` — not loaded
automatically, read it only if you need to know *why*, not just *what*.

## Working rhythm

- Start from the filled-in `01_PROBLEM_INTAKE_TEMPLATE.md` and
  `02_SOLUTION_ARCHITECTURE_TEMPLATE.md` the user pastes in. Don't re-derive the problem
  from scratch — treat those docs as the source of truth for scope.
- Update `03_BUILD_TRACKER_TEMPLATE.md` as you go if the user is tracking it in this repo
  — check things off, don't just report status in chat.
- Use the agents in `.claude/agents/` and the skills in `.claude/skills/` for their
  specific jobs (see the table above) rather than doing everything in the main thread —
  this is a solo hackathon entry competing against teams, and parallelizing
  architect/build/test/docs work is the whole strategy. See `00_GAME_PLAN.md` for why.
- When scope needs to be cut (and it will), say so explicitly and suggest what to cut —
  don't silently under-deliver, and don't silently over-build past what fits the time
  left either.
- No dependency installs or infra beyond what's needed for the demo (auth, multi-user
  support, persistence layers) unless the problem statement specifically demands it.
  Deployment to a free public host is the one exception — that's required, not scope
  creep — see `14_DEPLOYMENT_GUIDE.md`.

## Definition of done for any given work session here

- The core happy path runs, live, end-to-end, without manual patching
- It comes up from a single run command, no manual setup steps
  (`15_DEMO_RUNTIME_AND_TCMS_FLOW.md` §3)
- The 2-3 most likely failure modes are either handled or the demo script routes around
  them explicitly (never silently hope they don't come up)
- Output/UI is readable by a non-technical judge — no raw stack traces, no unexplained
  JSON dumps in the demo path
- The user can explain, in one sentence each: what problem this solves, why it's an
  agent, and what it saves someone

## What not to do

- Don't loop silently on a stubborn bug. 3 attempts, then stop and report what you
  tried and what happened — see `rapid-builder`'s circuit-breaker rule. This applies to
  any agent that iterates on a fix, not just that one.
- Don't introduce testing frameworks, CI, linting setups, or other infra scaffolding
  unless it directly serves the demo or the QE pass — this is a day-one throwaway repo
- Don't add auth, multi-user support, persistence layers, or other "production" concerns
  unless the problem statement specifically demands them for the demo
- Do deploy to a free public host once the build is stable — see
  `14_DEPLOYMENT_GUIDE.md`. This one *is* required: a live URL is part of the
  sellable-product pitch, not scope creep. Pick the target during design, not after
  the build is done.
- Don't wait for the user to ask for a test pass before sprint 2 — proactively suggest
  running the QE guardian pass once the happy path works, per the game plan schedule
- Don't write the pitch deck from scratch — `presentation.html` in this kit is the actual
  deck; fill its placeholders in once content is real instead of drafting slides elsewhere
- Don't re-summarize state that already lives in a file (the build tracker, the
  architecture doc) — read it instead of regenerating it, and keep explanations of
  decisions brief (a sentence or two) rather than verbose reports; see
  `08_TOKEN_EFFICIENCY_PLAYBOOK.md` for the full reasoning
