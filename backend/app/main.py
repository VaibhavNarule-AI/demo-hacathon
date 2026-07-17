import datetime
import os
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse
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
    CloseIncidentRequest,
    CreateIncidentRequest,
    CreatePartnerCustomerRequest,
    LoginRequest,
    MeResponse,
    RegisterPartnerRequest,
    SlaConfigRequest,
)
from app.repositories.customer_repository import fetch_customers, get_customer
from app.repositories.db import init_db
from app.repositories.incident_repository import (
    close_incident_row,
    create_incident,
    fetch_incidents,
    get_incident_by_id,
    next_ticket_number,
)
from app.repositories.partner_repository import (
    create_customer_for_partner,
    create_partner,
    fetch_partner_customers,
    fetch_partners,
    get_partner,
)
from app.repositories.sla_config_repository import (
    build_sla_lookup,
    fetch_sla_configs_for_partner,
    resolve_sla_minutes,
    upsert_sla_config,
)
from app.services import auth_service
from app.services.analytics_service import RangeTooLargeError, compute_kpis, compute_trends, resolve_range
from app.services.breach_predictor import compute_breach_risk
from app.services.health_score import compute_customer_health

app = FastAPI(title="PulseSOC — SOC Executive Command Center API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RangeTooLargeError)
def range_too_large_handler(request: Request, exc: RangeTooLargeError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


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
    date_from, date_to = resolve_range(filters)
    filters["date_from"], filters["date_to"] = date_from.isoformat(), date_to.isoformat()
    return fetch_incidents(filters, tenant_filter)


@app.get("/api/incidents/{incident_id}")
def incident_detail(incident_id: int, current_user: CurrentUser = Depends(get_current_user)):
    tenant_filter = get_tenant_filter(current_user)
    row = get_incident_by_id(incident_id, tenant_filter)
    if row is None:
        raise HTTPException(status_code=404, detail="Incident not found or out of scope")
    return row


VALID_SEVERITIES = ("Critical", "Major", "Minor", "Informational")


@app.post("/api/incidents/create", status_code=201)
def create_incident_route(
    payload: CreateIncidentRequest,
    current_user: CurrentUser = Depends(require_role("analyst", "super_admin")),
):
    if payload.severity not in VALID_SEVERITIES:
        raise HTTPException(status_code=400, detail=f"severity must be one of {VALID_SEVERITIES}")

    customer = get_customer(payload.customer)
    if customer is None:
        raise HTTPException(status_code=404, detail="Unknown customer")
    if current_user.role != "super_admin" and customer["partner_id"] != current_user.partner_id:
        write_flow_log(
            f"403 - {current_user.username} tried to create an incident for "
            f"{payload.customer} (partner={customer['partner_id']}) outside their own partner scope"
        )
        raise HTTPException(status_code=403, detail="Cannot create an incident outside your partner scope")

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    ticket_number = next_ticket_number(datetime.datetime.now(datetime.timezone.utc).year)
    incident = create_incident({
        "ticket_number": ticket_number,
        "partner": customer["partner_id"],
        "customer": payload.customer,
        "severity": payload.severity,
        "status": "Open",
        "service_type": customer["service_tier"],
        "siem": payload.siem,
        "soar": payload.soar,
        "sla_result": "none",
        "event_time": now,
        "created_time": now,
        # Opened immediately, not left pre-triage -- a manually-raised live
        # ticket needs to enter the SLA breach countdown right away, which is
        # exactly what the breach predictor / war room demo depends on.
        "opened_time": now,
        "first_response_time": None,
        "closed_time": None,
        "assigned_analyst": payload.assigned_analyst,
        "category": payload.category,
        "summary": payload.summary,
        "mitre_techniques": "",
        "false_positive": 0,
    })

    write_flow_log(
        f"201 - {ticket_number} created by {current_user.username} "
        f"(role={current_user.role}) for customer={payload.customer} partner={customer['partner_id']}"
    )
    return incident


def _parse_utc(dt_str):
    dt = datetime.datetime.fromisoformat(dt_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt


@app.post("/api/incidents/{incident_id}/close")
def close_incident_route(
    incident_id: int,
    payload: CloseIncidentRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    tenant_filter = get_tenant_filter(current_user)
    row = get_incident_by_id(incident_id, tenant_filter)
    if row is None:
        raise HTTPException(status_code=404, detail="Incident not found or out of scope")
    if row["closed_time"]:
        raise HTTPException(status_code=400, detail="Incident is already closed")
    if row["opened_time"] is None:
        raise HTTPException(status_code=400, detail="Cannot close an incident that was never opened")

    now = datetime.datetime.now(datetime.timezone.utc)
    opened_time = _parse_utc(row["opened_time"])
    elapsed_minutes = (now - opened_time).total_seconds() / 60

    customer_specific, partner_default = build_sla_lookup({"partner": row["partner"]})
    target_minutes = resolve_sla_minutes(
        customer_specific, partner_default, row["partner"], row["customer"], row["severity"]
    )
    sla_result = "Matched" if target_minutes is None or elapsed_minutes <= target_minutes else "Breached"

    updated = close_incident_row(incident_id, tenant_filter, now.isoformat(), sla_result, payload.resolution_notes)

    sla_saved_message = None
    if sla_result == "Matched" and target_minutes is not None:
        remaining = round(target_minutes - elapsed_minutes)
        sla_saved_message = f"SLA saved with {remaining} min left!"
        write_flow_log(f"SLA SAVED - {row['ticket_number']} closed by {current_user.username} ({remaining} min to spare)")
    else:
        write_flow_log(f"SLA BREACHED - {row['ticket_number']} closed by {current_user.username} after it had already breached")

    return {**updated, "sla_saved_message": sla_saved_message}


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


@app.get("/api/analytics/breach-risk")
def analytics_breach_risk(current_user: CurrentUser = Depends(get_current_user)):
    tenant_filter = get_tenant_filter(current_user)
    risk = compute_breach_risk(tenant_filter)
    high = [r for r in risk if r["risk"] == "HIGH"]
    if high:
        tickets = ", ".join(r["ticket_number"] for r in high)
        write_flow_log(f"breach-risk: {len(high)} HIGH risk incident(s) ({tickets})")
    blinking = [r for r in risk if r["blinking_critical"]]
    if blinking:
        tickets = ", ".join(r["ticket_number"] for r in blinking)
        write_flow_log(f"breach-risk: {len(blinking)} BLINKING_CRITICAL ({tickets})")
    return risk


@app.get("/api/analytics/customer-health")
def analytics_customer_health(current_user: CurrentUser = Depends(get_current_user)):
    tenant_filter = get_tenant_filter(current_user)
    return compute_customer_health(tenant_filter)


# ---------------------------------------------------------------------------
# /api/customers -- customers-service
# ---------------------------------------------------------------------------


@app.get("/api/customers")
def list_customers(current_user: CurrentUser = Depends(get_current_user)):
    tenant_filter = get_tenant_filter(current_user)
    return fetch_customers(tenant_filter)


# ---------------------------------------------------------------------------
# /api/sla-config -- per-partner/customer SLA override (feeds breach_predictor)
# ---------------------------------------------------------------------------


def _require_own_partner(current_user: CurrentUser, partner_id: str):
    if current_user.role != "super_admin" and partner_id != current_user.partner_id:
        raise HTTPException(status_code=403, detail="Cannot manage SLA/partner config outside your own partner")


@app.get("/api/sla-config")
def get_sla_config(
    partner: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    _require_own_partner(current_user, partner)
    return fetch_sla_configs_for_partner(partner)


@app.post("/api/sla-config", status_code=201)
def set_sla_config(
    payload: SlaConfigRequest,
    current_user: CurrentUser = Depends(require_role("super_admin", "partner_manager")),
):
    if payload.severity not in ("Critical", "Major", "Minor"):
        raise HTTPException(status_code=400, detail="severity must be Critical, Major, or Minor")
    _require_own_partner(current_user, payload.partner_id)

    config = upsert_sla_config(
        payload.partner_id, payload.customer_id, payload.severity, payload.sla_minutes, current_user.username
    )
    scope = f"{payload.partner_id}/{payload.customer_id}" if payload.customer_id else payload.partner_id
    write_flow_log(
        f"SLA config: {current_user.username} set {payload.severity} SLA to {payload.sla_minutes} min for {scope}"
    )
    return config


# ---------------------------------------------------------------------------
# /api/partners -- partner registration + onboarding
# ---------------------------------------------------------------------------


@app.post("/api/partners/register", status_code=201)
def register_partner(
    payload: RegisterPartnerRequest,
    current_user: CurrentUser = Depends(require_role("super_admin")),
):
    if get_partner(payload.partner_id) is not None:
        raise HTTPException(status_code=409, detail=f"Partner id '{payload.partner_id}' already exists")
    partner = create_partner(payload.partner_name, payload.partner_id, payload.contact_email)
    write_flow_log(f"Partner registered: {payload.partner_id} ({payload.partner_name}) by {current_user.username}")
    return partner


@app.get("/api/partners/list")
def list_partners(current_user: CurrentUser = Depends(require_role("super_admin"))):
    return fetch_partners()


@app.get("/api/partners/{partner_id}/customers")
def list_partner_customers(partner_id: str, current_user: CurrentUser = Depends(get_current_user)):
    _require_own_partner(current_user, partner_id)
    return fetch_partner_customers(partner_id)


@app.post("/api/partners/{partner_id}/customers/create", status_code=201)
def create_partner_customer(
    partner_id: str,
    payload: CreatePartnerCustomerRequest,
    current_user: CurrentUser = Depends(require_role("super_admin", "partner_manager")),
):
    _require_own_partner(current_user, partner_id)
    if get_partner(partner_id) is None:
        raise HTTPException(status_code=404, detail=f"Unknown partner '{partner_id}'")
    if get_customer(payload.customer_id) is not None:
        raise HTTPException(status_code=409, detail=f"Customer id '{payload.customer_id}' already exists")

    customer = create_customer_for_partner(
        partner_id, payload.customer_id, payload.customer_name, payload.service_tier, payload.siem, payload.soar
    )
    write_flow_log(
        f"Customer created: {payload.customer_id} ({payload.customer_name}) under {partner_id} by {current_user.username}"
    )
    return customer


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
