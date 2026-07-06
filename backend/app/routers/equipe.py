"""Gestão de equipe da clínica (owner) — adicionar/listar profissionais.

Habilita o cenário multiprofissional: o owner cria contas de `profissional` no
seu tenant. Cada profissional só enxerga os próprios pacientes (ver `app.authz`);
o owner enxerga todos.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select

from app.authz import is_owner
from app.deps import SessionDep, get_current_user
from app.models.audit import AuditLog
from app.models.user import User
from app.schemas.auth import EquipeMembroOut, ProfissionalCreate
from app.security.password import hash_password

router = APIRouter(prefix="/equipe", tags=["equipe"])


async def require_owner(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    if not is_owner(user):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Apenas o responsável (owner) da clínica pode gerenciar a equipe.",
        )
    return user


def _to_out(u: User) -> EquipeMembroOut:
    return EquipeMembroOut(
        id=str(u.id), nome=u.nome, email=u.email, papel=u.papel,
        crp=u.crp, crp_verificado=u.crp_verificado, totp_ativado=u.totp_ativado,
    )


@router.get("", response_model=list[EquipeMembroOut])
async def listar(
    session: SessionDep,
    owner: Annotated[User, Depends(require_owner)],
) -> list[EquipeMembroOut]:
    q = select(User).where(User.tenant_id == owner.tenant_id).order_by(User.criado_em)
    return [_to_out(u) for u in (await session.scalars(q)).all()]


@router.post("/profissionais", response_model=EquipeMembroOut, status_code=status.HTTP_201_CREATED)
async def criar_profissional(
    body: ProfissionalCreate,
    request: Request,
    session: SessionDep,
    owner: Annotated[User, Depends(require_owner)],
) -> EquipeMembroOut:
    existing = await session.scalar(select(User).where(User.email == body.email.lower()))
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email já cadastrado")

    novo = User(
        tenant_id=owner.tenant_id,
        email=body.email.lower(),
        senha_hash=hash_password(body.senha),
        nome=body.nome,
        crp=body.crp,
        abordagem=body.abordagem,
        papel="profissional",
    )
    session.add(novo)
    await session.flush()
    ip = request.client.host if request.client else None
    session.add(AuditLog(
        tenant_id=owner.tenant_id, user_id=owner.id, ip=ip,
        acao="EQUIPE_PROFISSIONAL_ADD", entidade="User", entidade_id=str(novo.id),
        meta={"email": novo.email},
    ))
    await session.commit()
    await session.refresh(novo)
    return _to_out(novo)
