# Deployment — Streamlit Community Cloud

Local repo is already committed on `main`. Remaining steps need your own GitHub and
Streamlit accounts.

1. Create a new GitHub repo (e.g. `hr-interview-summarizer`) at github.com/new —
   don't initialize it with a README.
2. Push this repo to it:
   ```
   git remote add origin <your-new-repo-url>
   git push -u origin main
   ```
3. Go to [share.streamlit.io](https://share.streamlit.io) → sign in with GitHub →
   "New app" → pick your repo/branch → set main file path to `app/app.py`.
4. In the app's settings → Secrets, add:
   ```
   ANTHROPIC_API_KEY = "your-real-key-here"
   ```
5. Deploy, then test the live public URL twice with real notes before presenting —
   the actual Claude call was never verified live in the build environment (no key
   available there), per `03_BUILD_TRACKER_TEMPLATE.md`.

Fallback if Streamlit Cloud has any account/setup friction: Hugging Face Spaces with
the Streamlit SDK, same `app/` contents.
