from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.conformidade.ia_cfp import tcle_ia
from app.deps import SessionDep, get_current_user
from app.models.consentimento import Consentimento
from app.models.paciente import Paciente
from app.models.user import User
from app.schemas.clinico import ConsentimentoCreate, ConsentimentoOut, TcleIaOut

router = APIRouter(prefix="/consentimentos", tags=["consentimentos"])


@router.get("/tcle-ia", response_model=TcleIaOut)
async def obter_tcle_ia(
    _user: Annotated[User, Depends(get_current_user)],
) -> TcleIaOut:
    """Texto versionado do TCLE de uso de IA (Res. CFP 09/2024) para registro."""
    return TcleIaOut(**tcle_ia())


def _to_out(c: Consentimento) -> ConsentimentoOut:
    return ConsentimentoOut(
        id=str(c.id), paciente_id=str(c.paciente_id), tipo=c.tipo,
        texto_aceito=c.texto_aceito, aceito_por=c.aceito_por, aceito_em=c.aceito_em,
    )


@router.post("", response_model=ConsentimentoOut, status_code=status.HTTP_201_CREATED)
async def registrar(
    body: ConsentimentoCreate,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> ConsentimentoOut:
    pac = await session.get(Paciente, uuid.UUID(body.paciente_id))
    if not pac or pac.tenant_id != user.tenant_id or pac.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Paciente não encontrado")
    c = Consentimento(
        tenant_id=user.tenant_id, paciente_id=pac.id, tipo=body.tipo,
        texto_aceito=body.texto_aceito, aceito_por=body.aceito_por,
    )
    session.add(c)
    await session.commit()
    await session.refresh(c)
    return _to_out(c)


@router.get("/paciente/{paciente_id}", response_model=list[ConsentimentoOut])
async def listar(
    paciente_id: str,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> list[ConsentimentoOut]:
    q = select(Consentimento).where(
        Consentimento.tenant_id == user.tenant_id,
        Consentimento.paciente_id == uuid.UUID(paciente_id),
    ).order_by(Consentimento.aceito_em.desc())
    return [_to_out(c) for c in (await session.scalars(q)).all()]
