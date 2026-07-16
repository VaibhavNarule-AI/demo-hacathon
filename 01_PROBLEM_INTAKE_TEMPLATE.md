# Problem Intake

## Use case
An HR tool that helps an HR person manage all candidates and maintain their data after
each interview.

## Core AI feature (this hackathon's scope)
Interview note summarization: HR types/pastes free-text notes for a candidate after an
interview. The agent reads the raw notes and produces a structured summary per
candidate — strengths, concerns, and an overall rating/recommendation.

## Input
Free-text notes typed directly into the app by HR (no file upload, no transcript
ingestion).

## Primary user
HR person managing candidates end-to-end (single-user for the demo — no auth/multi-user
per `CLAUDE.md` scope rules).

## Out of scope for this build
- Candidate ranking/comparison across candidates
- Natural-language Q&A search over candidate history
- Auto-drafted follow-up emails
(These are logical next features if there's time left after the core happy path works.)

## Success looks like
Live demo: HR pastes notes for a candidate → agent returns a clean structured summary
(strengths / concerns / rating) → summary is stored against that candidate's record so
it persists as "data maintained after interview."
