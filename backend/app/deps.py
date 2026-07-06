"""Dependências FastAPI comuns (auth, sessão + tenant scope)."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import jwt

from app.db import (
    SessionLocal,
    current_request_ip,
    current_tenant_id,
    current_user_id,
)
from app.middleware.audit import install as install_audit
from app.models.user import User
from app.security.jwt import decode_token


async def scoped_session(request: Request) -> AsyncSession:
    """Sessão SQLAlchemy async com hooks de audit instalados."""
    async with SessionLocal() as session:
        install_audit(session)
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


SessionDep = Annotated[AsyncSession, Depends(scoped_session)]


class Principal:
    __slots__ = ("user_id", "tenant_id", "mfa_verified", "scope")

    def __init__(self, user_id: str, tenant_id: str, mfa_verified: bool, scope: str):
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.mfa_verified = mfa_verified
        self.scope = scope


def _extract_token(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token ausente")
    return authorization.split(" ", 1)[1].strip()


async def get_principal(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
) -> Principal:
    token = _extract_token(authorization)
    try:
        payload = decode_token(token)
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Token inválido: {e}")

    p = Principal(
        user_id=payload["sub"],
        tenant_id=payload["tid"],
        mfa_verified=bool(payload.get("mfa")),
        scope=payload.get("scope", "session"),
    )
    # popula contextvars para audit
    current_user_id.set(p.user_id)
    current_tenant_id.set(p.tenant_id)
    current_request_ip.set(request.client.host if request.client else None)
    return p


async def require_session(principal: Annotated[Principal, Depends(get_principal)]) -> Principal:
    """Requer JWT de escopo 'session' com MFA verificado (ou usuário sem TOTP ativo)."""
    if principal.scope != "session":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Escopo insuficiente")
    return principal


# Código estruturado do 403 de "2FA obrigatório, ainda não configurado". O
# frontend intercepta este code para redirecionar ao onboarding de 2FA (é 403,
# não 401 — 401 limparia o token e cairia no loop de login).
MFA_SETUP_REQUIRED = "2fa_setup_required"


async def _load_user(session: AsyncSession, principal: Principal) -> User:
    user = await session.scalar(select(User).where(User.id == uuid.UUID(principal.user_id)))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não existe")
    if str(user.tenant_id) != principal.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant divergente")
    return user


async def get_user_sem_gate_2fa(
    principal: Annotated[Principal, Depends(require_session)],
    session: SessionDep,
) -> User:
    """Usuário de sessão SEM exigir 2FA ativo — só para o próprio onboarding de
    2FA (`/auth/me`, `/auth/2fa/setup`, `/auth/2fa/verify`). Fora disso, use
    `get_current_user`, que bloqueia acesso clínico sem 2FA."""
    return await _load_user(session, principal)


async def require_mfa_verified(
    principal: Annotated[Principal, Depends(require_session)],
    session: SessionDep,
) -> Principal:
    """2FA obrigatório: bloqueia sessão clínica sem TOTP ativo (403 com code
    para o frontend levar ao setup) e exige mfa=True no JWT."""
    user = await session.get(User, uuid.UUID(principal.user_id))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não existe")
    if not user.totp_ativado:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": MFA_SETUP_REQUIRED,
                "message": "Configure a verificação em duas etapas (2FA) para acessar dados clínicos.",
            },
        )
    if not principal.mfa_verified:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="2FA obrigatório")
    return principal


async def get_current_user(
    principal: Annotated[Principal, Depends(require_mfa_verified)],
    session: SessionDep,
) -> User:
    return await _load_user(session, principal)
