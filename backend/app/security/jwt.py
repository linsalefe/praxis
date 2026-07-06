"""Emissão e verificação de JWT."""
import uuid
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
    auth_at: int | None = None,
    token_versao: int = 0,
    extra: dict[str, Any] | None = None,
) -> str:
    s = get_settings()
    now = datetime.now(tz=timezone.utc)
    ttl = ttl_minutes if ttl_minutes is not None else s.jwt_ttl_minutes
    iat = int(now.timestamp())
    payload: dict[str, Any] = {
        "sub": user_id,
        "tid": tenant_id,
        "mfa": mfa_verified,
        "scope": scope,
        "iat": iat,
        "exp": int((now + timedelta(minutes=ttl)).timestamp()),
        # jti: identifica o token para revogação server-side (blocklist). Cada
        # emissão/renovação recebe um jti novo.
        "jti": uuid.uuid4().hex,
        # tv: versão do token do usuário — "encerrar todas as sessões" incrementa
        # a versão no banco, invalidando todos os tokens com tv anterior.
        "tv": token_versao,
    }
    # auth_at fixa o momento do login (não o iat, que muda a cada renovação):
    # é o âncora do teto absoluto de sessão. Emitido no login e copiado nas
    # renovações. Só faz sentido em tokens de sessão.
    if scope == "session":
        payload["auth_at"] = int(auth_at) if auth_at is not None else iat
    if extra:
        payload.update(extra)
    return jwt.encode(payload, s.jwt_secret, algorithm=s.jwt_alg)


def decode_token(token: str) -> dict[str, Any]:
    s = get_settings()
    return jwt.decode(token, s.jwt_secret, algorithms=[s.jwt_alg])
