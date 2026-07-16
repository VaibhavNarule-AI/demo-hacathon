# Demo Script — Interview Note Summarizer

Total live-demo budget: **~2:30** (out of a 5:00 hard limit, leaving time for the pitch
slides + buffer). Practice this twice, out loud, before presenting — per the QE pass's
own recommendation.

## Setup, before you go on stage (do this beforehand, not while presenting)

- [ ] Docker Desktop running, `minikube start --driver=docker` already up
- [ ] `minikube service demo-hacathon --url` running in one terminal window (keep it
      open, off-screen)
- [ ] `cloudflared tunnel --url http://127.0.0.1:<port>` running in a second terminal
      window (keep it open, off-screen) — note the public URL it printed
- [ ] Public URL opened once already in your browser tab, ready to go (avoids a live
      DNS/loading wait in front of the jury)
- [ ] One candidate already saved from a prior test run, so "reopen and see it persisted"
      has something real to show without typing it live
- [ ] A second, fresh browser tab or the same tab reloaded — ready for the live paste

## The sequence

**1. Open on the candidate list (5 sec)**
> "This is a small internal tool for HR — after every interview, notes pile up
> somewhere, and pulling a clear read on a candidate means re-reading all of it by hand."

Point at the sidebar dropdown — show the one pre-saved candidate is there, with their
notes and summary already loaded.

> "Here's [Name] from an earlier interview — the notes and this summary were saved
> last time. It's still here because it's backed by real storage, not just this
> browser session."

**2. Add a new candidate, live (10 sec)**
- Click **"+ Add new candidate"**
- Type a name (pick something short, memorable)

**3. Paste notes and summarize (20-30 sec, mostly waiting on the model or the mock)**
- Paste a short, realistic block of notes into the textarea (have this pre-written in
  a note app, don't type it live — copy/paste only)
- Click **Summarize**

> "It's not keyword-matching — it's reading the notes the way a person would, and
> making a judgment call: what's a real strength, what's only implied as a concern,
> and an overall recommendation."

**4. Show the result (10 sec)**

Read the Strengths / Concerns / Rating / Recommendation out loud, briefly — don't just
point at the screen and go silent.

**If the "⚠️ DEMO MODE" banner is showing** (no live API key — see note below), say this
line exactly, confidently, once:
> "This is running in a demo mode with a mocked response right now — our company
> policy blocks provisioning a new Anthropic API key today, so I'm showing the exact
> structure and UX it produces; wiring in a live key is a one-line config change, not
> a rebuild."

**5. Save and prove persistence (10 sec)**
- Click **Save**
- Reload the page (or switch to the pre-saved candidate and back)

> "That's saved against this candidate's record now — next time anyone opens this
> tool, it's there. No re-reading the original notes needed."

## What NOT to do live (per the QE pass, `03_BUILD_TRACKER_TEMPLATE.md`)

- **Don't switch candidates while notes are typed but not yet saved** — it silently
  discards the draft (by design, not a bug). Finish one candidate's flow
  (notes → Summarize → Save) before opening another.
- **Don't trigger a rebuild/redeploy right before or during the demo** — the SQLite
  storage resets on pod/container restart. Everything should already be running and
  stable before you go on.
- If asked "does this call the real Claude API?" — answer with the demo-mode line
  above, don't dodge it. Judges respect an honest "here's the real constraint we hit
  and how we routed around it" more than a smoothed-over claim.

## The payoff moment

The single thing this sequence should land: **unstructured, scattered interview notes
go in; a consistent, structured hiring judgment comes out — and it's actually saved,
not just displayed once and gone.** Everything else (the candidate list, the styling)
is scaffolding around that one moment.
