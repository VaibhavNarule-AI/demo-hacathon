# Solution Architecture — Interview Note Summarizer

## 1. One-page design

**Flow:** HR opens the app → picks or adds a candidate → pastes free-text interview
notes into a text box → clicks "Summarize" → the agent returns a structured summary
(strengths / concerns / overall rating & recommendation) → HR clicks "Save" → the
summary is written to that candidate's record and shows up when they reopen the app.

**Pieces, and why each is boring on purpose:**
| Piece | Choice | Why |
|---|---|---|
| Interface | Streamlit (single page, Python) | One file, no HTML/CSS/JS to hand-write, looks like a finished internal tool out of the box |
| Agent / reasoning | Claude API, structured output (JSON schema) | The one place we spend "smart" — see §2 |
| Storage | SQLite, one local file (`candidates.db`) | No database server to configure, no ORM, survives the process lifetime, trivial to inspect |
| Deployment | Streamlit Community Cloud | Free, deploys straight from a GitHub repo, gives a public URL in minutes |

## 1.5 Competitive scan (fast)

Greenhouse/Lever (ATS) only give you a free-text scorecard field — no summarization at
all. BrightHire/Metaview/HireVue "interview intelligence" tools do AI summaries, but only
from recorded/transcribed calls, need integration setup, and are priced for enterprise
teams. Nothing in this space takes **notes HR already typed by hand** and turns them into
a structured, judgment-based summary in seconds with zero setup — that gap, not "it uses
AI," is what this demo is built to show.

## 2. Why this counts as an agent, not a script

A script would keyword-match ("mentions 'communication' → tag: soft skill"). This agent
**reasons over the notes**: it infers concerns the notes imply but never state outright,
weighs conflicting signals (e.g. strong technical notes but a hesitant tone about
teamwork) into one overall recommendation, and returns that judgment in a fixed structure
(strengths / concerns / rating) every time, regardless of how messy or differently-worded
the input is. That interpretive step — going from unstructured human judgment to a
consistent structured verdict — is the part a script can't do reliably; it's the whole
reason this is worth calling an agent.

## 3. Top 3 failure modes (hand off to QE pass)

1. **Bad/partial structured output** — the model returns text that isn't valid JSON, or
   skips a field, under a weird or very short note. *Mitigate:* enforce the JSON schema
   in the API call, wrap parsing in a retry-once-then-show-a-clear-error path, never show
   a raw stack trace to the judge.
2. **Storage resets under you** — Streamlit Community Cloud can restart/redeploy the app,
   which wipes the local SQLite file since there's no persistent volume on the free tier.
   *Mitigate:* pre-seed 1-2 candidates before the demo, don't trigger a redeploy right
   before presenting, keep a local copy of the db file as backup.
3. **API hiccup live** (timeout, rate limit, or a missing key in the deployed
   environment specifically, even if it works locally). *Mitigate:* set the API key as a
   secret in Streamlit's own secrets manager (not hardcoded), test the *deployed* URL
   twice beforehand, not just localhost.

## 4. Deployment target

**Streamlit Community Cloud**, deployed from a GitHub repo containing the Streamlit app
+ `requirements.txt`. Free, no credit card, gives a public `*.streamlit.app` URL as soon
as it's connected. (Hugging Face Spaces with the Streamlit SDK is an equally valid
fallback if Streamlit Cloud has any account/setup friction on the day.)

## Build-first instruction

Build the happy path first: a single Streamlit page with a notes textarea and a
"Summarize" button that calls the Claude API with a fixed JSON schema and prints the
result on screen — get that working end-to-end with one hardcoded candidate before
touching SQLite storage or the candidate list UI.
