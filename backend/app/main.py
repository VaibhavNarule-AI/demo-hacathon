import os
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from app.core.auth import (
    CurrentUser,
    get_current_user,
    get_tenant_filter,
    require_role,
    write_flow_log,
)
from app.core.config import FRONTEND_DIST, TESTCASES_DIR
from app.models.schemas import (
    AsyncLoginAccepted,
    AsyncLoginStatus,
    LoginRequest,
    MeResponse,
)
from app.repositories.customer_repository import fetch_customers
from app.repositories.db import init_db
from app.repositories.incident_repository import fetch_incidents, get_incident_by_id
from app.services import auth_service
from app.services.analytics_service import compute_kpis, compute_trends

app = FastAPI(title="SOC Executive Dashboard API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


# ---------------------------------------------------------------------------
# /api/auth -- auth-service
# ---------------------------------------------------------------------------


@app.post("/api/auth/login")
def login(payload: LoginRequest):
    result = auth_service.authenticate(payload.username, payload.password)
    if result is None:
        write_flow_log(f"401 - login failed for {payload.username}")
        raise HTTPException(status_code=401, detail="Invalid username or password")
    write_flow_log(f"200 - login success for {payload.username} (role={result.role})")
    return result


@app.post("/api/auth/login-async", response_model=AsyncLoginAccepted)
def login_async(payload: LoginRequest):
    job_id = auth_service.start_async_login(payload.username, payload.password)
    return AsyncLoginAccepted(job_id=job_id)


@app.get("/api/auth/status/{job_id}", response_model=AsyncLoginStatus)
def login_status(job_id: str):
    result, status = auth_service.get_async_login_result(job_id)
    if status == "not_found":
        raise HTTPException(status_code=404, detail="Unknown job_id")
    return AsyncLoginStatus(job_id=job_id, status=status, result=result)


@app.get("/api/auth/me", response_model=MeResponse)
def me(current_user: CurrentUser = Depends(get_current_user)):
    return MeResponse(**current_user.model_dump())


# ---------------------------------------------------------------------------
# /api/incidents -- incidents-service
# ---------------------------------------------------------------------------


def _query_filters(customer, siem, soar, tier, from_, to, partner):
    return {
        "customer": customer,
        "siem": siem,
        "soar": soar,
        "tier": tier,
        "date_from": from_,
        "date_to": to,
        "partner": partner,
    }


@app.get("/api/incidents")
def list_incidents(
    customer: Optional[str] = None,
    siem: Optional[str] = None,
    soar: Optional[str] = None,
    tier: Optional[str] = None,
    from_: Optional[str] = Query(None, alias="from"),
    to: Optional[str] = None,
    partner: Optional[str] = None,
    current_user: CurrentUser = Depends(get_current_user),
):
    tenant_filter = get_tenant_filter(current_user)
    filters = _query_filters(customer, siem, soar, tier, from_, to, partner)
    return fetch_incidents(filters, tenant_filter)


@app.get("/api/incidents/{incident_id}")
def incident_detail(incident_id: int, current_user: CurrentUser = Depends(get_current_user)):
    tenant_filter = get_tenant_filter(current_user)
    row = get_incident_by_id(incident_id, tenant_filter)
    if row is None:
        raise HTTPException(status_code=404, detail="Incident not found or out of scope")
    return row


# ---------------------------------------------------------------------------
# /api/analytics -- analytics-service (all KPI math is in analytics_service.py)
# ---------------------------------------------------------------------------


@app.get("/api/analytics/kpis")
def analytics_kpis(
    customer: Optional[str] = None,
    siem: Optional[str] = None,
    soar: Optional[str] = None,
    tier: Optional[str] = None,
    from_: Optional[str] = Query(None, alias="from"),
    to: Optional[str] = None,
    partner: Optional[str] = None,
    current_user: CurrentUser = Depends(get_current_user),
):
    tenant_filter = get_tenant_filter(current_user)
    filters = _query_filters(customer, siem, soar, tier, from_, to, partner)
    return compute_kpis(filters, tenant_filter)


@app.get("/api/analytics/trends")
def analytics_trends(
    metric: str = Query("volume", pattern="^(volume|mttr)$"),
    bucket: str = "weekly",
    customer: Optional[str] = None,
    siem: Optional[str] = None,
    soar: Optional[str] = None,
    tier: Optional[str] = None,
    from_: Optional[str] = Query(None, alias="from"),
    to: Optional[str] = None,
    partner: Optional[str] = None,
    current_user: CurrentUser = Depends(get_current_user),
):
    tenant_filter = get_tenant_filter(current_user)
    filters = _query_filters(customer, siem, soar, tier, from_, to, partner)
    return compute_trends(metric, filters, tenant_filter)


# ---------------------------------------------------------------------------
# /api/customers -- customers-service
# ---------------------------------------------------------------------------


@app.get("/api/customers")
def list_customers(current_user: CurrentUser = Depends(get_current_user)):
    tenant_filter = get_tenant_filter(current_user)
    return fetch_customers(tenant_filter)


# ---------------------------------------------------------------------------
# Ops endpoints
# ---------------------------------------------------------------------------


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/demo/reset")
def demo_reset(current_user: CurrentUser = Depends(require_role("super_admin"))):
    import subprocess
    import sys

    subprocess.run([sys.executable, "seed.py"], check=True, cwd=Path(__file__).resolve().parent.parent)
    return {"status": "reseeded"}


@app.get("/test-report", response_class=HTMLResponse)
def test_report():
    path = Path(TESTCASES_DIR) / "test_report.html"
    if not path.exists():
        raise HTTPException(status_code=404, detail="test_report.html not generated yet")
    return FileResponse(path)


@app.get("/flow", response_class=PlainTextResponse)
def flow():
    from app.core.config import FLOW_LOG_PATH

    path = Path(FLOW_LOG_PATH)
    if not path.exists():
        return "No flow activity logged yet."
    lines = path.read_text().splitlines()
    return "\n".join(lines[-5:])


# ---------------------------------------------------------------------------
# Frontend static hosting (SPA)
# ---------------------------------------------------------------------------

_assets_dir = Path(FRONTEND_DIST) / "assets"
if _assets_dir.is_dir():
    app.mount("/assets", StaticFiles(directory=str(_assets_dir)), name="assets")


@app.get("/")
def serve_index():
    index_path = Path(FRONTEND_DIST) / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "Frontend not built yet. Run `npm run build` in frontend/."}


@app.get("/{full_path:path}")
def spa_fallback(full_path: str):
    index_path = Path(FRONTEND_DIST) / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    raise HTTPException(status_code=404, detail="Not found")
