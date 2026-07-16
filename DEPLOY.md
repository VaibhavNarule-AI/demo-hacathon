# Deployment — Docker + Kubernetes (Gruve Inc cluster)

This is the primary deployment path — Docker image pushed to Docker Hub
(`vaibhavnarule23/demo_hackathon`), run on the company's existing Kubernetes cluster.
Chosen over Streamlit Cloud/Render because it uses infra you already have access to,
instead of external accounts blocked by company/network policy.

All of these steps need to run on your own machine — this build environment has no
`docker` or `kubectl` installed and no network path to Docker Hub or your company's
cluster, so I can't run them for me. `app/Dockerfile`, `k8s/deployment.yaml`, and
`k8s/service.yaml` are already committed; you just need to build, push, and apply.

**1. Build and push the image** (from the `app/` directory):
```
cd app
docker build -t vaibhavnarule23/demo_hackathon:latest .
docker login -u vaibhavnarule23
docker push vaibhavnarule23/demo_hackathon:latest
```
When `docker login` asks for a password, type/paste your Docker Hub password or
access token directly into the terminal prompt — don't paste it here in chat.

**2. Create the API key secret** (only if you have a working `ANTHROPIC_API_KEY` —
skip this if not, the app runs fine in mocked demo mode without it):
```
kubectl create secret generic demo-hacathon-secrets \
  --from-literal=ANTHROPIC_API_KEY=your-real-key-here
```

**3. Apply the manifests:**
```
kubectl apply -f ../k8s/deployment.yaml
kubectl apply -f ../k8s/service.yaml
```

**4. Get the public URL/IP:**
```
kubectl get service demo-hacathon
```
Wait for `EXTERNAL-IP` to populate (can take a minute or two on first creation), then
open `http://<EXTERNAL-IP>` in a browser.

If your cluster doesn't support `LoadBalancer` (some internal/on-prem clusters don't
auto-provision a public IP), change `type: LoadBalancer` to `type: ClusterIP` in
`k8s/service.yaml` and use `kubectl port-forward service/demo-hacathon 8501:80`
instead, or ask your cluster admin about an Ingress if you have one set up.

**Note:** the SQLite storage inside the container resets whenever the pod restarts
(same known limitation as the cloud-hosted options below) — pre-seed a candidate or
two before presenting, same as documented in `03_BUILD_TRACKER_TEMPLATE.md`.

---

# Fallback — Streamlit Community Cloud

Kept as a working fallback since this was already deployed and verified live before
switching to Kubernetes. Local repo is already committed on `main`.

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
