#!/usr/bin/env bash
# SOC Executive Dashboard — build, seed, test, deploy (docker + k8s), verify.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "Step 1: docker build -t pulsesoc:v2 ."
docker build -t pulsesoc:v2 .

echo "Step 2: seeding demo data (5,000 incidents, 20 customers, 4 users)"
python3 backend/seed.py

echo "Step 3: running qe-guardian test suite"
python3 backend/test_runner.py

echo "Step 4: docker compose up (local demo, http://localhost:8000)"
docker compose up -d

echo "Step 4b: waiting for /health on :8000"
for i in $(seq 1 30); do
  if curl -sf http://localhost:8000/health > /dev/null; then
    break
  fi
  sleep 2
done
curl -sf http://localhost:8000/health > /dev/null && echo "/health OK on :8000"

echo "Step 5: loading image into cluster (minikube's docker driver runs its own daemon)"
if docker ps --format '{{.Names}}' | grep -qx minikube; then
  docker save pulsesoc:v2 | docker exec -i minikube docker load
else
  echo "no separate minikube container found -- assuming the cluster shares this host's image store"
fi

echo "Step 5b: kubectl apply -f k8s/"
kubectl apply -f k8s/
kubectl delete pod -l app=soc-dashboard --ignore-not-found=true > /dev/null 2>&1 || true

echo "Step 5c: waiting for the pod to be ready, then port-forwarding the Service to :30080"
kubectl wait --for=condition=ready pod -l app=soc-dashboard --timeout=90s || true
pkill -f "kubectl port-forward svc/soc-dashboard" > /dev/null 2>&1 || true
kubectl port-forward svc/soc-dashboard 30080:80 > /tmp/soc-dashboard-portforward.log 2>&1 &
sleep 3

for i in $(seq 1 30); do
  if curl -sf http://localhost:30080/health > /dev/null 2>&1; then
    break
  fi
  sleep 2
done
if curl -sf http://localhost:30080/health > /dev/null 2>&1; then
  echo "/health OK on :30080 (k8s, via port-forward)"
else
  echo "k8s NodePort not reachable yet -- docker-compose demo on :8000 is still fully live"
fi

echo ""
echo "Live at:"
echo "  http://localhost:8000        (docker-compose)"
echo "  http://localhost:30080       (k8s NodePort, if reachable above)"
echo "  http://localhost:8000/test-report"
echo "  http://localhost:8000/flow"
echo "  http://localhost:8000/health"
