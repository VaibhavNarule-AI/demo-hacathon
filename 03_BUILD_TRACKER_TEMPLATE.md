# Build Tracker — QE Guardian Pass (Sprint 2: candidates + SQLite storage)

Date: 2026-07-16
Tester: qe-guardian (adversarial pass, no real ANTHROPIC_API_KEY available in this
environment — everything reachable without a successful Claude call was exercised)

## Method note

Streamlit's built-in `streamlit.testing.v1.AppTest` (Streamlit 1.39.0, already installed
in `app/.venv`) was used to drive real widget interactions (selectbox, text_input,
text_area, button clicks) against the actual `app.py` script, in addition to booting the
real server with `streamlit run app.py --server.headless true` and confirming it serves
HTTP 200 on first request with no manual setup step beyond the (expected, documented)
`ANTHROPIC_API_KEY` and `pip install -r requirements.txt`. No real API key was available
or used, so the actual Claude summarization call was never exercised — this pass focuses
entirely on everything else the app does.

## Known issues

| Issue | Severity | Demo-time workaround | Fixed or open |
|---|---|---|---|
| `get_api_key()` accessed `st.secrets["ANTHROPIC_API_KEY"]` even when no `secrets.toml` exists anywhere on disk. Streamlit's own secrets loader calls `st.error()` internally in that case (exposing local file paths like `/Users/.../.streamlit/secrets.toml`) *before* raising, so the judge would see two stacked red error boxes: Streamlit's raw internal one, then the app's clean "No ANTHROPIC_API_KEY found..." message. Not a crash, but a confusing/technical-looking message that shouldn't appear in front of a judge. | Medium (cosmetic but violates "no raw/unreadable output in front of a judge") | N/A — fixed | **Fixed.** `get_api_key()` now checks `st.config.get_option("secrets.files")` for an existing file before touching `st.secrets` at all. Re-verified via AppTest: only the single clean error message now appears when no key/secrets file exists. |
| Switching candidates (or navigating to "+ Add new candidate") while notes are typed but not yet saved silently discards the in-progress text — no confirmation prompt, no crash, no warning. | Low (expected behavior for an unsaved draft, but easy to trip over live) | Don't switch candidates mid-sentence during the live demo. Finish typing notes → Summarize → Save for one candidate before opening another. Narrate as "notes are drafts until you click Save" if it comes up. | Open (by design — not a bug, just a UX sharp edge; not a proportionate same-day fix) |
| SQLite storage resets if the deployed app (Streamlit Community Cloud) redeploys/restarts — no persistent volume on the free tier. Pre-identified at design time in `02_SOLUTION_ARCHITECTURE_TEMPLATE.md` §3. | Medium (only matters for the *deployed* demo, not local) | Pre-seed 1-2 candidates before presenting, don't trigger a redeploy right before/during the demo, keep a local copy of `candidates.db` as backup. | Open (known/accepted risk per design doc, not a code bug) |
| Live API hiccup (timeout/rate-limit/missing key in the deployed environment specifically) — could not be exercised end-to-end here since no real key was available in this environment. Code path (`try/except` around `call_claude_for_summary`, field-presence validation, `st.error` with details) reads correctly and the *missing-key* case was verified directly to show a clean message, not a traceback. | Medium (untested with a live key) | Before presenting, test the *deployed* URL with the real key at least twice, per the design doc's own mitigation — don't rely on this pass as proof the happy path itself renders correctly. | Open (out of scope for this environment — no key available) |
| Minor: `NotOpenSSLWarning` printed to the server terminal log on every boot (LibreSSL vs OpenSSL mismatch in this Python build). | Cosmetic/negligible | Server-log noise only, never reaches the Streamlit UI. Ignore; don't let it look alarming if visible on a shared screen during setup. | Open (environment quirk, not app code, not worth touching) |

## Checks performed and passed cleanly (no issues)

- Boot via single command `streamlit run app.py --server.headless true`, twice, from a
  clean `candidates.db` — HTTP 200 both times, no manual setup step besides the
  documented API key / `pip install -r requirements.txt`.
- Full demo sequence (open app → add candidate → type notes → switch candidates →
  reopen) run twice back-to-back via AppTest — no stale-state bugs, no exceptions,
  candidate list and notes reload correctly both times.
- Blank candidate name: subheader correctly shows "(unnamed — type a name in the
  sidebar)", no crash.
- Blank notes + Summarize: clean `st.warning("Paste some interview notes first.")`,
  no crash, no API call attempted.
- Save button: confirmed it does not even render until a summary exists in
  `st.session_state` — clicking "Save before Summarize" is structurally impossible
  through the UI, not just guarded after the fact.
- Full Save → reload flow (simulated a Claude response to isolate this from the API
  itself): saved correctly to SQLite, reload shows persisted notes + summary, no
  exceptions.
- No raw Python tracebacks observed in the Streamlit UI or server log at any point in
  this pass, before or after the one fix above.

## Go / No-Go verdict

**GO** — safe to demo as scripted, with one narrated workaround: don't switch candidates
mid-typing without saving first (notes are drafts until Saved, by design). The one real
bug found (duplicate/confusing error box on the missing-API-key path) has been fixed and
re-verified. The two remaining open items (SQLite reset on redeploy, live API hiccup) are
pre-identified design-time risks, not code bugs — mitigate per the design doc (pre-seed
candidates, test the deployed URL with the real key beforehand) rather than by further
code changes tonight.
