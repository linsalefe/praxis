"""Rotas de autenticação: registro, login, 2FA (setup/verify/login)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy import select

from app.db import current_request_ip, current_tenant_id, current_user_id
from app.deps import (
    Principal,
    SessionDep,
    _extract_token,
    get_current_user,
    get_principal,
    get_user_sem_gate_2fa,
)
from app.models.audit import AuditLog
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.auth import (
    LoginIn,
    MeOut,
    PerfilUpdateIn,
    RegisterIn,
    TokenOut,
    TotpLoginIn,
    TotpSetupOut,
    TotpVerifyIn,
)
from app.security.crypto import decrypt_str, encrypt_str
from app.security.jwt import decode_token, make_token
from app.security.password import hash_password, verify_password
from app.security.throttle import (
    chave_conta,
    chave_ip,
    registrar_falha,
    registrar_sucesso,
    verificar_bloqueio,
)
from app.security.totp import build_uri, generate_secret, qr_png_datauri, verify

router = APIRouter(prefix="/auth", tags=["auth"])

# Sliding session: só renova a ≤15min do exp; teto absoluto de 12h a partir do
# login (auth_at). Nada disso cria refresh token nem altera o TTL do access token.
_JANELA_RENOVACAO_S = 15 * 60
_TETO_SESSAO_S = 12 * 60 * 60


def _me_out(user: User) -> MeOut:
    return MeOut(
        id=str(user.id), nome=user.nome, email=user.email, crp=user.crp,
        crp_verificado=user.crp_verificado,
        abordagem=user.abordagem, papel=user.papel, totp_ativado=user.totp_ativado,
        tenant_id=str(user.tenant_id),
        nome_exibicao=user.nome_exibicao,
        registro_profissional=user.registro_profissional,
        contato_timbre=user.contato_timbre,
    )


async def _log(session, *, acao: str, entidade: str, entidade_id: str | None, tenant_id, user_id, ip, meta=None):
    session.add(
        AuditLog(
            tenant_id=tenant_id,
            user_id=user_id,
            acao=acao,
            entidade=entidade,
            entidade_id=entidade_id,
            ip=ip,
            meta=meta or {},
        )
    )


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterIn, request: Request, session: SessionDep) -> TokenOut:
    existing = await session.scalar(select(User).where(User.email == body.email))
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email já cadastrado")

    tenant = Tenant(tipo=body.tenant_tipo, nome=body.tenant_nome)
    session.add(tenant)
    await session.flush()

    user = User(
        tenant_id=tenant.id,
        email=body.email.lower(),
        senha_hash=hash_password(body.senha),
        nome=body.nome,
        crp=body.crp,
        abordagem=body.abordagem,
        papel="owner",
    )
    session.add(user)
    await session.flush()

    ip = request.client.host if request.client else None
    await _log(
        session, acao="REGISTER", entidade="User", entidade_id=str(user.id),
        tenant_id=tenant.id, user_id=user.id, ip=ip,
    )
    await session.commit()

    token = make_token(user_id=str(user.id), tenant_id=str(tenant.id), mfa_verified=True)
    return TokenOut(access_token=token, mfa_required=False, scope="session")


@router.post("/login", response_model=TokenOut)
async def login(body: LoginIn, request: Request, session: SessionDep) -> TokenOut:
    ip = request.client.host if request.client else None
    chaves = [chave_conta(body.email), chave_ip(ip)]
    await verificar_bloqueio(session, chaves)

    user = await session.scalar(select(User).where(User.email == body.email.lower()))
    if not user or not verify_password(body.senha, user.senha_hash):
        await registrar_falha(session, chaves)
        await _log(session, acao="LOGIN_FALHA", entidade="Auth",
                   entidade_id=(str(user.id) if user else None),
                   tenant_id=(user.tenant_id if user else None),
                   user_id=(user.id if user else None), ip=ip,
                   meta={"email": body.email.lower(), "motivo": "credenciais"})
        await session.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciais inválidas")

    await registrar_sucesso(session, chaves)

    if user.totp_ativado:
        # Emite token pré-2FA (escopo diferente).
        pre = make_token(
            user_id=str(user.id), tenant_id=str(user.tenant_id),
            mfa_verified=False, scope="pre_2fa", ttl_minutes=5,
        )
        await _log(session, acao="LOGIN", entidade="User", entidade_id=str(user.id),
                   tenant_id=user.tenant_id, user_id=user.id, ip=ip, meta={"mfa": "required"})
        await session.commit()
        return TokenOut(access_token=pre, mfa_required=True, scope="pre_2fa")

    tok = make_token(user_id=str(user.id), tenant_id=str(user.tenant_id), mfa_verified=True)
    await _log(session, acao="LOGIN", entidade="User", entidade_id=str(user.id),
               tenant_id=user.tenant_id, user_id=user.id, ip=ip, meta={"mfa": "none"})
    await session.commit()
    return TokenOut(access_token=tok, mfa_required=False, scope="session")


@router.post("/2fa/setup", response_model=TotpSetupOut)
async def totp_setup(
    session: SessionDep,
    user: Annotated[User, Depends(get_user_sem_gate_2fa)],
) -> TotpSetupOut:
    if user.totp_ativado:
        raise HTTPException(status.HTTP_409_CONFLICT, "2FA já ativado")
    secret = generate_secret()
    user.totp_secret_cifrado = encrypt_str(secret)  # ainda não ativado — precisa de verify.
    await session.commit()
    uri = build_uri(secret, user.email)
    return TotpSetupOut(otpauth_url=uri, qrcode_data_uri=qr_png_datauri(uri))


@router.post("/2fa/verify", response_model=MeOut)
async def totp_verify(
    body: TotpVerifyIn,
    request: Request,
    session: SessionDep,
    user: Annotated[User, Depends(get_user_sem_gate_2fa)],
) -> MeOut:
    if not user.totp_secret_cifrado:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Setup 2FA não iniciado")

    ip = request.client.host if request.client else None
    chaves = [chave_conta(str(user.id)), chave_ip(ip)]
    await verificar_bloqueio(session, chaves)

    secret = decrypt_str(user.totp_secret_cifrado) or ""
    if not verify(secret, body.codigo):
        await registrar_falha(session, chaves)
        await _log(session, acao="ENABLE_2FA_FALHA", entidade="User", entidade_id=str(user.id),
                   tenant_id=user.tenant_id, user_id=user.id, ip=ip)
        await session.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Código inválido")

    await registrar_sucesso(session, chaves)
    user.totp_ativado = True
    await _log(session, acao="ENABLE_2FA", entidade="User", entidade_id=str(user.id),
               tenant_id=user.tenant_id, user_id=user.id, ip=ip)
    await session.commit()
    return _me_out(user)


@router.post("/2fa/login", response_model=TokenOut)
async def totp_login(
    body: TotpLoginIn,
    request: Request,
    session: SessionDep,
    principal: Annotated[Principal, Depends(get_principal)],
) -> TokenOut:
    if principal.scope != "pre_2fa":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Escopo inválido — faça login primeiro")

    ip = request.client.host if request.client else None
    chaves = [chave_conta(principal.user_id), chave_ip(ip)]
    await verificar_bloqueio(session, chaves)

    user = await session.get(User, uuid.UUID(principal.user_id))
    if not user or not user.totp_ativado or not user.totp_secret_cifrado:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "2FA não configurado")
    secret = decrypt_str(user.totp_secret_cifrado) or ""
    if not verify(secret, body.codigo):
        await registrar_falha(session, chaves)
        await _log(session, acao="LOGIN_2FA_FALHA", entidade="User", entidade_id=str(user.id),
                   tenant_id=user.tenant_id, user_id=user.id, ip=ip)
        await session.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Código 2FA inválido")

    await registrar_sucesso(session, chaves)
    await _log(session, acao="LOGIN_2FA", entidade="User", entidade_id=str(user.id),
               tenant_id=user.tenant_id, user_id=user.id, ip=ip)
    await session.commit()

    tok = make_token(user_id=str(user.id), tenant_id=str(user.tenant_id), mfa_verified=True)
    return TokenOut(access_token=tok, mfa_required=False, scope="session")


@router.get("/me", response_model=MeOut)
async def me(user: Annotated[User, Depends(get_user_sem_gate_2fa)]) -> MeOut:
    return _me_out(user)


@router.patch("/me", response_model=MeOut)
async def atualizar_perfil(
    body: PerfilUpdateIn,
    request: Request,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> MeOut:
    """Atualiza os campos de timbre do perfil. Só mexe no que veio no corpo;
    string vazia limpa o campo (volta ao fallback nome/crp na geração de PDF)."""
    campos = body.model_dump(exclude_unset=True)
    for campo, valor in campos.items():
        if isinstance(valor, str):
            valor = valor.strip() or None
        setattr(user, campo, valor)

    ip = request.client.host if request.client else None
    await _log(session, acao="PERFIL_ATUALIZADO", entidade="User", entidade_id=str(user.id),
               tenant_id=user.tenant_id, user_id=user.id, ip=ip,
               meta={"campos": sorted(campos.keys())})
    await session.commit()
    await session.refresh(user)
    return _me_out(user)


@router.post(
    "/renovar",
    response_model=TokenOut,
    responses={204: {"description": "Fora da janela de renovação ou sessão no teto — manter o token atual"}},
)
async def renovar(
    request: Request,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
    authorization: Annotated[str | None, Header()] = None,
):
    """Renovação silenciosa de sessão (sliding session).

    A dependência ``get_current_user`` já garante token válido, não expirado,
    escopo ``session`` e MFA satisfeito — logo, token inválido/expirado/pré-2FA
    cai em 401 antes daqui. Emite um novo access token (mesmos claims/escopo e
    TTL padrão) apenas quando o atual está a ≤15min do ``exp`` e a sessão ainda
    não passou do teto absoluto. Não cria refresh token nem estende o expirado.
    """
    payload = decode_token(_extract_token(authorization))  # já validado pela dependência
    now = int(datetime.now(tz=timezone.utc).timestamp())

    # Fora da janela final do TTL: no-op (cliente mantém o token atual).
    if payload["exp"] - now > _JANELA_RENOVACAO_S:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    # Teto absoluto de sessão. Tokens emitidos antes deste deploy não têm
    # auth_at → 204: a pessoa reloga uma vez (dentro do TTL) e passa a ter o claim.
    auth_at = payload.get("auth_at")
    if auth_at is None or now - int(auth_at) > _TETO_SESSAO_S:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    tok = make_token(
        user_id=str(user.id), tenant_id=str(user.tenant_id),
        mfa_verified=True, auth_at=int(auth_at),
    )
    ip = request.client.host if request.client else None
    await _log(session, acao="RENEW_SESSION", entidade="User", entidade_id=str(user.id),
               tenant_id=user.tenant_id, user_id=user.id, ip=ip)
    await session.commit()
    return TokenOut(access_token=tok, mfa_required=False, scope="session")
