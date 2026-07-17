import uuid
from typing import Optional

from app.core.auth import CurrentUser, create_access_token, hash_password, verify_password
from app.models.schemas import TokenResponse
from app.repositories.user_repository import get_user_by_email

# In-memory job store for the async login demo endpoint. A hackathon-scale
# stand-in for a real task queue -- fine for a single-process demo, not meant
# to survive a restart.
_login_jobs: dict = {}

# Fixed dummy hash so a nonexistent email still pays the bcrypt cost --
# without this, "no such user" returns near-instantly while "wrong password"
# takes ~100ms+, letting an attacker enumerate valid emails by timing.
_DUMMY_HASH = hash_password("not-a-real-password")


def authenticate(email: str, password: str) -> Optional[TokenResponse]:
    row = get_user_by_email(email)
    if row is None:
        verify_password(password, _DUMMY_HASH)
        return None
    if not verify_password(password, row["password_hash"]):
        return None
    user = CurrentUser(
        email=row["email"],
        role=row["role"],
        partner_id=row["partner_id"],
        customer_id=row["customer_id"],
    )
    token = create_access_token(user)
    return TokenResponse(
        access_token=token,
        role=user.role,
        partner_id=user.partner_id,
        customer_id=user.customer_id,
    )


def start_async_login(email: str, password: str) -> str:
    job_id = str(uuid.uuid4())
    result = authenticate(email, password)
    # Computed synchronously here since auth is fast; job_id/status endpoint
    # still models the real async contract for a slower auth provider later.
    if result is not None:
        _login_jobs[job_id] = result
    else:
        _login_jobs[job_id] = None
    return job_id


def get_async_login_result(job_id: str):
    if job_id not in _login_jobs:
        return None, "not_found"
    result = _login_jobs[job_id]
    if result is None:
        return None, "failed"
    return result, "complete"
