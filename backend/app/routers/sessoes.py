"""CRUD de Sessao."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.deps import SessionDep, get_current_user
from app.models.paciente import Paciente
from app.models.sessao import Sessao
from app.models.user import User
from app.schemas.clinico import SessaoCreate, SessaoOut, SessaoUpdate

router = APIRouter(prefix="/sessoes", tags=["sessoes"])


def _to_out(s: Sessao) -> SessaoOut:
    return SessaoOut(
        id=str(s.id), paciente_id=str(s.paciente_id), data=s.data,
        modalidade=s.modalidade, status=s.status, criado_em=s.criado_em,
    )


@router.post("", response_model=SessaoOut, status_code=status.HTTP_201_CREATED)
async def criar(
    body: SessaoCreate,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> SessaoOut:
    pac = await session.get(Paciente, uuid.UUID(body.paciente_id))
    if not pac or pac.tenant_id != user.tenant_id or pac.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Paciente não encontrado")
    s = Sessao(
        tenant_id=user.tenant_id, paciente_id=pac.id,
        data=body.data, modalidade=body.modalidade, status=body.status,
    )
    session.add(s)
    await session.commit()
    await session.refresh(s)
    return _to_out(s)


@router.get("/paciente/{paciente_id}", response_model=list[SessaoOut])
async def listar_por_paciente(
    paciente_id: str,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> list[SessaoOut]:
    q = select(Sessao).where(
        Sessao.tenant_id == user.tenant_id,
        Sessao.paciente_id == uuid.UUID(paciente_id),
    ).order_by(Sessao.data.desc())
    rows = list((await session.scalars(q)).all())
    return [_to_out(s) for s in rows]


@router.patch("/{sessao_id}", response_model=SessaoOut)
async def atualizar(
    sessao_id: str,
    body: SessaoUpdate,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> SessaoOut:
    s = await session.get(Sessao, uuid.UUID(sessao_id))
    if not s or s.tenant_id != user.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sessão não encontrada")
    if body.data is not None:
        s.data = body.data
    if body.modalidade is not None:
        s.modalidade = body.modalidade
    if body.status is not None:
        s.status = body.status
    await session.commit()
    await session.refresh(s)
    return _to_out(s)
