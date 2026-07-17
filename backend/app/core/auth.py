import datetime
import os
from pathlib import Path
from typing import Optional

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.core.config import JWT_ALGORITHM, JWT_EXPIRE_MINUTES, JWT_SECRET, FLOW_LOG_PATH

security = HTTPBearer(auto_error=False)

ROLES = ("super_admin", "partner_manager", "customer_viewer", "analyst")


class CurrentUser(BaseModel):
    username: str
    role: str
    partner_id: Optional[str] = None
    customer_id: Optional[str] = None


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(user: CurrentUser) -> str:
    expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
        minutes=JWT_EXPIRE_MINUTES
    )
    payload = {
        "sub": user.username,
        "role": user.role,
        "partner_id": user.partner_id,
        "customer_id": user.customer_id,
        "exp": expire,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def write_flow_log(line: str) -> None:
    path = Path(FLOW_LOG_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with path.open("a") as f:
        f.write(f"[{timestamp}] {line}\n")


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> CurrentUser:
    if credentials is None or not credentials.credentials:
        write_flow_log("401 - missing bearer token")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        write_flow_log("401 - expired token")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        write_flow_log("401 - invalid token")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = CurrentUser(
        username=payload["sub"],
        role=payload["role"],
        partner_id=payload.get("partner_id"),
        customer_id=payload.get("customer_id"),
    )
    write_flow_log(
        f"200 - token verified for {user.username} (role={user.role}, "
        f"partner={user.partner_id}, customer={user.customer_id})"
    )
    return user


def require_role(*allowed_roles: str):
    def _dependency(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if current_user.role not in allowed_roles:
            write_flow_log(
                f"403 - {current_user.username} (role={current_user.role}) "
                f"denied, requires one of {allowed_roles}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return current_user

    return _dependency


def get_tenant_filter(current_user: CurrentUser) -> dict:
    """Server-side tenant scope. Query-string params the caller sends are never
    trusted directly for partner/customer -- this is the only source of truth."""
    if current_user.role == "super_admin":
        return {}
    if current_user.role == "customer_viewer":
        return {"partner": current_user.partner_id, "customer": current_user.customer_id}
    # partner_manager and analyst are both scoped to their own partner only
    return {"partner": current_user.partner_id}
