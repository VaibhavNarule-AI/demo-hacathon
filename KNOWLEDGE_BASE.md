# Knowledge Base — Interview Note Summarizer

Retrospective analysis of this entire build (conversation, requirements, app, code,
deployment, and documents), extracted for reuse by an AI application development
framework. Machine-readable companion: `knowledge_base.json`.

---

## 1. Business Problem

HR is left with unstructured, hand-typed interview notes and no consistent way to
turn them into a hiring decision — manual re-reading is slow and produces
inconsistent conclusions across reviewers.

**Market gap:** ATS tools (Greenhouse/Lever) offer only a free-text scorecard, no
summarization. Interview-intelligence tools (BrightHire/Metaview/HireVue) do AI
summarization but require recorded/transcribed calls, integration setup, and
enterprise pricing. Nothing takes notes HR already typed by hand and returns a
structured judgment with zero setup — that's the wedge this fills.

## 2. User Roles

Single role for this MVP: **HR / Hiring Manager** — full access, no role
differentiation, no auth (explicit scope cut for a one-day disposable build).

## 3. Functional Requirements

- Add/select a candidate
- Paste free-text interview notes
- Trigger AI summarization on demand
- Receive structured output: strengths, concerns, overall rating, recommendation
- Persist notes + summary against the candidate
- Reload a candidate's saved data automatically on reselect
- Run in a labeled mocked-fallback mode when no live API key is configured

## 4. Non-Functional Requirements

- Single-command startup, no manual setup beyond documented API key + install
- No auth/multi-user/heavy persistence layer (explicit scope cut)
- Never surface a raw stack trace to an end user
- Bounded, predictable AI-call cost
- Must have a fully offline/no-external-account fallback path
- Deployable without a paid or approval-gated account
- Portable across multiple hosting targets with zero app-code changes

## 5. Features

**Implemented:** candidate picker, free-text notes input, AI structured
summarization (forced tool-use), SQLite persistence, save/reload, mocked demo mode,
clean error handling (missing key / blank input / malformed AI response), multi-target
deployment (Docker + Kubernetes + Cloudflare Tunnel, with Streamlit Cloud/Render/remote
cluster documented as fallbacks).

**Planned, not built:** shortlist ranking with comparative reasoning,
natural-language Q&A across candidate history, auto-drafted follow-up
communications, live API integration (blocked by company policy, not a technical
gap).

## 6. Workflow

Open app → pick/add candidate → paste notes → Summarize (real call or mocked
fallback) → structured result rendered → Save → persisted to SQLite → reselecting
that candidate later reloads notes + summary automatically.

## 7. Business Rules

- Candidate name is unique (no duplicates)
- Notes are draft-only until Save is clicked (switching candidates discards drafts —
  accepted tradeoff, not a bug)
- Save button only renders once a summary exists — can't save before summarizing
- A missing/invalid API key never surfaces as a raw error — resolves to a mocked
  result or a single clean message
- An AI response missing a required field is treated as invalid, not partially
  trusted

## 8. UI Screens

Single-page app: sidebar candidate picker (existing + "add new"), main panel with
candidate subheader, notes textarea, Summarize button, conditional result panel
(strengths/concerns/rating/recommendation + optional demo-mode banner), conditional
Save button.

## 9. Database Schema

SQLite, single file (`candidates.db`), one table:

| Column | Type | Notes |
|---|---|---|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| name | TEXT | UNIQUE NOT NULL |
| notes | TEXT | |
| strengths | TEXT | JSON-encoded array |
| concerns | TEXT | JSON-encoded array |
| overall_rating | INTEGER | |
| recommendation | TEXT | |
| updated_at | TEXT | ISO 8601 UTC |

Upsert-by-name via `INSERT ... ON CONFLICT(name) DO UPDATE`.

## 10. APIs & Integrations

**Anthropic Claude API** (`anthropic` Python SDK, model `claude-sonnet-5`). Single
`messages.create()` call, `tool_choice` forcing one named tool
(`record_interview_summary`) with a strict `input_schema`
(strengths/concerns/overall_rating/recommendation, `additionalProperties: false`).
Auth via `ANTHROPIC_API_KEY` env var, falling back to Streamlit secrets (guarded by
a file-existence check to avoid a framework-internal error leak).

## 11. Validations

Blank notes blocked before any API call; blank candidate name handled without a
crash; AI response validated for required fields before rendering; API key presence
checked before every summarization attempt.

## 12. Authentication

Not implemented — explicit scope cut for a single-user internal tool. A
productionized version would need per-recruiter accounts and row-level access
control.

## 13. Reusable Components / Patterns

- **Forced-tool-call structured output** — reusable for any "extract structured
  judgment from unstructured text" feature
- **Env-var-first, existence-checked secrets fallback** — avoids framework-internal
  error leakage when reading a secret
- **Mocked-mode graceful degradation** — a single boolean branch keeps a demo
  usable when an external credential is unavailable; switching to live is a
  zero-code-change config addition
- **SQLite upsert-by-unique-key** — simple persistence without a migration
  framework
- **Draft-until-saved session state** — explicit, documented tradeoff instead of
  silent ambiguity
- **Platform-agnostic containerized app** — same Dockerfile/app code prepared or
  deployed across 4 different hosting targets with zero app changes
- **No-signup public tunnel** (`cloudflared tunnel --url`) — reusable fallback
  whenever normal cloud hosting is blocked by org policy or account friction

## 14. Best Practices Applied

Adversarial QE pass before calling anything done (caught a real bug pre-launch);
never show raw stack traces; written known-issues log with severity + workaround;
relaxed version pins after a real platform-compatibility break rather than fighting
it; secrets never committed to source; a pasted credential was treated as
compromised immediately regardless of intended use; deployment decisions documented
with real reasoning, not just the final answer.

---

## 15. What Worked Well

- Specialized sub-agents (architecture / build / QE) kept each pass focused; the QE
  pass caught a real bug the build pass didn't
- The mocked-mode fallback turned a hard external blocker (no obtainable API key)
  into a fully demoable app instead of a dead end
- Diagnosing deployment failures from actual error/log output (not guessing) led to
  fast, correct fixes — e.g. the Python 3.14/pillow wheel issue, the DNS-resolver
  discrepancy
- The same app code stayed stable across every deployment pivot, proving the
  architecture wasn't the problem — the hosting environment was
- Verifying claims instead of trusting them (re-testing the public tunnel via a DNS
  bypass) correctly isolated an office-network DNS block as the real issue, not a
  broken deployment

## 16. What Was Missing Initially

- No upfront intake of the user's actual environment constraints (API-key policy,
  network/OAuth restrictions, existing cluster access) before choosing a
  deployment target — caused 3 reactive pivots
- No initial check that the hosting platform's Python/runtime version matched the
  pinned dependency versions
- No established secure channel for credential handoff at the start — a secret was
  pasted into chat twice despite being told not to, each time

## 17. Errors Encountered & Root Causes

| Error | Root Cause | Fix |
|---|---|---|
| `git push` failed: "could not read Username" | Non-interactive shell can't prompt for credentials; GitHub no longer accepts account passwords over HTTPS | Ran push in the user's own interactive terminal with a classic PAT (repo scope) |
| GitHub API repo creation: 403 "not accessible by personal access token" | Fine-grained PAT lacked account-level repo-creation permission | Abandoned automation; created repo manually via GitHub web UI |
| Streamlit Cloud build failed: pillow build error | Exact version pin pulled an old pillow with no wheel for the platform's Python 3.14 | Relaxed pins to `>=` so a compatible version resolved |
| Streamlit Cloud GitHub OAuth: 504 Gateway Timeout | Corporate proxy interfering with the OAuth callback | Retried from outside the office network |
| Anthropic Console org creation blocked | Company-wide admin policy on the work email domain | No resolution (IT declined); routed around via mocked demo mode |
| Credential pasted directly into chat (twice: GitHub PAT, ACR password) | User bypassed the requested file-based hand-off | Treated as compromised immediately, rotation recommended, not reused beyond the immediate step |
| `kubectl`/`docker` "command not found" in the automation shell | PATH didn't include Homebrew's install location, though tools were correctly installed | Invoked by full path / prepended `/opt/homebrew/bin` to PATH per command |
| sudo-gated installs failed in the automation shell | No interactive TTY for password entry | User ran those specific steps in their own terminal |
| Public tunnel URL unreachable for the user specifically | Office network's DNS resolver failed to resolve the tunnel hostname; public resolvers worked fine | Verified via DNS-bypassed test request; user worked around via hosts-file entry or different network |

## 18. Prompt Improvement Opportunities

1. **Structured intake up front** — an informal initial problem description
   required a full clarifying round-trip; a structured intake (business goal, core
   AI feature, input format, users) reduces this to one pass.
2. **Disambiguate one-word confirmations** — "yes"/"proceed" after a multi-option
   question is ambiguous and caused repeated re-asks; reference which option is
   being confirmed.
3. **Ask about deployment constraints before picking a target** — a single upfront
   question about company network/API/account restrictions would have surfaced the
   eventual blockers before any hosting attempt began, instead of 4 reactive
   pivots.
4. **Ask about content density/audience before building a deliverable** — the
   default "keep slides sparse" best practice didn't match this user's actual need
   (a dense technical+business deck); ask the audience/density question before
   applying a default style.
5. **Make the credential hand-off instruction a hard precondition, not an in-the-
   moment warning** — state the file-based hand-off requirement with a concrete
   path before a credential is ever needed, not just when one is first requested.

---

## 19. Optimized Prompt

A single upfront prompt template that reduces the iteration seen in this session to
one build pass, for similar "unstructured input → structured AI judgment →
persisted record" internal tools:

> Build a one-day MVP hackathon app: **[DOMAIN]**. Core AI feature: **[the single
> AI-powered transformation — e.g. "HR pastes free-text interview notes for a
> candidate; an AI agent extracts a structured summary (strengths, concerns,
> overall rating, recommendation) and persists it against that candidate's
> record"]**. Input format: **[free text / file upload / structured form]**.
> Primary user: **[role + auth/multi-user requirement]**.
>
> Before building, confirm these constraints so the deployment target is chosen
> correctly the first time:
> 1. Is there an existing, usable API key/credential for the AI provider, or an
>    organizational policy blocking provisioning a new one?
> 2. Does the company network block or filter OAuth sign-in flows, specific
>    domains/DNS, or public tunnel services?
> 3. Is there an existing remote server/cluster/registry already accessible with
>    confirmed working credentials, or should the target be a local-machine
>    deployment with a public tunnel?
> 4. Should the final deliverable be a sparse spoken-pitch deck or a dense
>    technical+business leave-behind document?
>
> Build order: (a) working core happy-path end-to-end with one hardcoded record
> before any persistence or secondary UI, (b) add persistence + full UI, (c) add a
> labeled mocked-response fallback that activates automatically whenever the real
> API key/credential is unavailable, so the app is always demoable regardless of
> question 1's answer, (d) run an adversarial QE pass (blank/malformed input,
> repeated runs, missing-credential path) and fix anything that would show a raw
> error to an end user, (e) deploy to the target from question 3, verifying
> end-to-end reachability — not just "it deployed" — before considering it done,
> (f) produce a demo script and a presentation matching the density from question 4.
>
> Hard rules: never accept a pasted credential/secret in conversation — always
> request it be saved to a file path outside the source repo, on the first ask,
> before it's ever needed. Never leave a build undemoable due to a missing external
> credential — always have a mocked fallback. Confirm which option is being
> actioned when given a one-word response to a multi-option question, rather than
> assuming.

Structured variables for framework templating: `domain`, `core_ai_transformation`,
`input_format`, `primary_user`, `api_key_availability`, `network_constraints`,
`deployment_target_hint`, `presentation_density` — see `knowledge_base.json` →
`optimized_prompt.structured_variables` for the full enum/type definitions.

---

## 20. Reusable Knowledge Base (machine-readable)

See `knowledge_base.json` in this repo for the full structured extraction (all
sections above, plus the errors table and optimized prompt) in a format intended
for direct ingestion by an AI application development framework.
