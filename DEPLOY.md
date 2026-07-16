# Deployment — Local Kubernetes (minikube) + Cloudflare Tunnel

This is the **working, currently-live** deployment path. Company/network policy
blocked every hosted option (Anthropic API org creation, GitHub OAuth for Streamlit
Cloud, and there was no confirmed `kubectl` access to a remote company cluster), so
the final setup runs entirely on your own Mac:

- **minikube** (local Kubernetes cluster, Docker driver) runs the app from
  `app/Dockerfile`, deployed via `k8s/deployment.yaml` + `k8s/service.yaml`.
- **cloudflared quick tunnel** exposes it publicly with zero signup/account needed,
  sidestepping the pattern of account/OAuth blocks hit with every other option.

## One-time setup (already done, for reference)
```
brew install --cask docker          # then open Docker.app once, let it fully start
brew install kubectl minikube cloudflared
```

## Every time you need it running (e.g. before presenting)
```
minikube start --driver=docker

cd app
eval $(minikube docker-env)
docker build -t demo-hacathon:local .
cd ..

kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl rollout status deployment/demo-hacathon
```

Get a local URL (keep this terminal window open — it's a live tunnel process):
```
minikube service demo-hacathon --url
```

Expose that local URL publicly (keep this terminal open too, in a second window):
```
cloudflared tunnel --url http://127.0.0.1:<port-from-previous-command>
```
It prints a `https://<random-words>.trycloudflare.com` URL — that's the one to share.

## Known caveats
- **Both terminal windows (the `minikube service` tunnel and `cloudflared` tunnel)
  must stay running, and your Mac must stay awake and connected**, for the whole
  window you might be asked to demo it — this is not a persistently-hosted cloud
  deployment.
- **Office network DNS blocks `trycloudflare.com`** (same pattern as other
  account/OAuth blocks hit during setup) — you personally may not be able to open the
  public URL from office wifi. Judges on their own network/device are unaffected.
  Workaround to test it yourself from office wifi:
  ```
  echo "<ip-from-dig> <your-tunnel-hostname>" | sudo tee -a /etc/hosts
  ```
  (get `<ip-from-dig>` via `dig +short <your-tunnel-hostname> @1.1.1.1`), or just use
  mobile data/hotspot instead.
- **No real `ANTHROPIC_API_KEY` is configured** — company policy blocks provisioning
  one (Anthropic Console org creation is blocked for the `gruve.ai` domain, and IT
  won't provision a key). The app runs in a labeled **mocked demo mode**: clicking
  "Summarize" shows a realistic but fake example result with a visible "⚠️ DEMO MODE"
  banner. Fully demoable, just narrate that honestly if asked. Swap in a real key any
  time (as a Kubernetes secret, see `k8s/deployment.yaml`'s `secretKeyRef`) and it
  switches to live Claude calls automatically, no code changes needed.
- **SQLite storage resets** whenever the pod restarts — pre-seed a candidate or two
  right before presenting, same known limitation logged in
  `03_BUILD_TRACKER_TEMPLATE.md`.

---

# Fallback options (not used, kept for reference)

These were attempted first and hit account/network blocks, but are documented in case
the local+tunnel setup becomes unavailable (e.g. laptop issue) and a hosted option is
worth retrying.

## Streamlit Community Cloud

1. Push this repo to a GitHub repo (already done — `VaibhavNarule-AI/demo-hacathon`).
2. Go to [share.streamlit.io](https://share.streamlit.io) → sign in with GitHub →
   "New app" → pick the repo/branch → set main file path to `app/app.py`.
3. In the app's settings → Secrets, add `ANTHROPIC_API_KEY = "your-real-key-here"`
   if you have one.
4. Deploy. Known issue hit here: pinned dependency versions in `app/requirements.txt`
   broke on Python 3.14 (pillow had no prebuilt wheel) — already fixed by relaxing the
   pins to `>=` instead of `==`.

Fallback of the fallback: Hugging Face Spaces with the Streamlit SDK, same `app/`
contents.

## Render.com

A `render.yaml` blueprint is committed at the repo root for this.
1. [dashboard.render.com](https://dashboard.render.com) → sign in with GitHub.
2. **New** → **Blueprint** → select the `demo-hacathon` repo → Render reads
   `render.yaml` automatically.
3. Paste your `ANTHROPIC_API_KEY` when prompted (marked `sync: false`, never stored
   in the repo).
4. Deploy — gives a public `https://demo-hacathon.onrender.com`-style URL. Free tier
   spins down after inactivity (~30s cold start on first hit after idle).

## Docker Hub + remote Kubernetes cluster

If a real remote cluster becomes accessible later: build/push to
`vaibhavnarule23/demo_hackathon` on Docker Hub, then `kubectl apply` the same
`k8s/deployment.yaml`/`k8s/service.yaml` after changing the `image:` field back to
`vaibhavnarule23/demo_hackathon:latest` and removing `imagePullPolicy: Never`.
