from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select

from app.conformidade.ia_cfp import tcle_ia
from app.deps import SessionDep, get_current_user
from app.models.audit import AuditLog
from app.models.consentimento import Consentimento
from app.models.paciente import Paciente
from app.models.user import User
from app.schemas.clinico import ConsentimentoCreate, ConsentimentoOut, TcleIaOut

router = APIRouter(prefix="/consentimentos", tags=["consentimentos"])


@router.get("/tcle-ia", response_model=TcleIaOut)
async def obter_tcle_ia(
    _user: Annotated[User, Depends(get_current_user)],
) -> TcleIaOut:
    """Texto versionado do TCLE de uso de IA (Nota de Posicionamento CFP sobre IA, 2025) para registro."""
    return TcleIaOut(**tcle_ia())


def _to_out(c: Consentimento) -> ConsentimentoOut:
    return ConsentimentoOut(
        id=str(c.id), paciente_id=str(c.paciente_id), tipo=c.tipo,
        texto_aceito=c.texto_aceito, aceito_por=c.aceito_por, aceito_em=c.aceito_em,
        revogado_em=c.revogado_em,
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


@router.post("/{consentimento_id}/revogar", response_model=ConsentimentoOut)
async def revogar(
    consentimento_id: str,
    request: Request,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> ConsentimentoOut:
    """Revoga um consentimento (LGPD art. 18). Append-only: marca `revogado_em`,
    não apaga a linha. A partir daí o fluxo correspondente (IA, gravação,
    teleatendimento) volta a ser bloqueado por falta de consentimento ativo."""
    try:
        cid = uuid.UUID(consentimento_id)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "consentimento_id inválido")
    c = await session.get(Consentimento, cid)
    if not c or c.tenant_id != user.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Consentimento não encontrado")
    if c.revogado_em is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Consentimento já revogado")
    c.revogado_em = func.now()
    session.add(AuditLog(
        tenant_id=user.tenant_id, user_id=user.id,
        ip=request.client.host if request.client else None,
        acao="CONSENTIMENTO_REVOGADO", entidade="Consentimento", entidade_id=str(c.id),
        meta={"tipo": c.tipo, "paciente_id": str(c.paciente_id)},
    ))
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
