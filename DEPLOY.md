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

## Alternative: Render.com

Used instead of Streamlit Cloud due to office-network OAuth issues. A `render.yaml`
blueprint is already committed at the repo root, so Render can configure the service
automatically.

1. Go to [dashboard.render.com](https://dashboard.render.com) → sign in with GitHub.
2. Click **New** → **Blueprint** → select the `demo-hacathon` repo → Render reads
   `render.yaml` and pre-fills the service (root dir `app`, build/start commands).
3. When prompted for the `ANTHROPIC_API_KEY` env var (marked `sync: false` in the
   blueprint so it's never stored in the repo), paste your real key.
4. Click **Apply** / **Create**. First deploy takes a few minutes on the free tier.
5. Render gives a public `https://demo-hacathon.onrender.com`-style URL — test the
   summarize flow twice with real notes before presenting.

Note: Render's free tier spins the service down after inactivity, so the first
request after a while will be slow (~30s cold start) — worth knowing before a live
demo, hit the URL once a minute or two beforehand to warm it up.
