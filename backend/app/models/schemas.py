from typing import Optional

from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    partner_id: Optional[str] = None
    customer_id: Optional[str] = None


class AsyncLoginAccepted(BaseModel):
    job_id: str
    status: str = "pending"


class AsyncLoginStatus(BaseModel):
    job_id: str
    status: str
    result: Optional[TokenResponse] = None


class MeResponse(BaseModel):
    username: str
    role: str
    partner_id: Optional[str] = None
    customer_id: Optional[str] = None


class CustomerOut(BaseModel):
    customer_id: str
    customer_name: str
    partner_id: str
    service_tier: str
    siem: str
    soar: str


class IncidentOut(BaseModel):
    id: int
    ticket_number: str
    partner: str
    customer: str
    severity: str
    status: str
    service_type: str
    siem: str
    soar: str
    sla_result: Optional[str]
    event_time: str
    created_time: str
    opened_time: Optional[str]
    first_response_time: Optional[str]
    closed_time: Optional[str]
    assigned_analyst: Optional[str]
    category: Optional[str]
    summary: Optional[str]
    mitre_techniques: Optional[str]
    false_positive: bool


class KPIDelta(BaseModel):
    value: Optional[float]
    previous: Optional[float]
    delta_pct: Optional[float]


class KPIResponse(BaseModel):
    alerts: KPIDelta
    critical_alerts: KPIDelta
    incidents: KPIDelta
    avg_mttd_minutes: KPIDelta
    avg_mttr_hours: KPIDelta
    sla_compliance_pct: KPIDelta
    sla_breaches: KPIDelta
    false_positive_rate_pct: KPIDelta
    p1_avg_response_minutes: KPIDelta
    p2_avg_response_minutes: KPIDelta
    p3_avg_response_minutes: KPIDelta


class TrendPoint(BaseModel):
    week_start: str
    values: dict
