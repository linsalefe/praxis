"""Emissão e verificação de JWT."""
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from app.config import get_settings


def make_token(
    *,
    user_id: str,
    tenant_id: str,
    mfa_verified: bool,
    scope: str = "session",
    ttl_minutes: int | None = None,
    extra: dict[str, Any] | None = None,
) -> str:
    s = get_settings()
    now = datetime.now(tz=timezone.utc)
    ttl = ttl_minutes if ttl_minutes is not None else s.jwt_ttl_minutes
    payload: dict[str, Any] = {
        "sub": user_id,
        "tid": tenant_id,
        "mfa": mfa_verified,
        "scope": scope,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=ttl)).timestamp()),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, s.jwt_secret, algorithm=s.jwt_alg)


def decode_token(token: str) -> dict[str, Any]:
    s = get_settings()
    return jwt.decode(token, s.jwt_secret, algorithms=[s.jwt_alg])
