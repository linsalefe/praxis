"""CRUD de Evolução com estrutura CFP e assinatura eletrônica."""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.deps import SessionDep, get_current_user
from app.models.audit import AuditLog
from app.models.evolucao import Evolucao
from app.models.evolucao_geracao import EvolucaoGeracao
from app.models.sessao import Sessao
from app.models.user import User
from app.schemas.clinico import EvolucaoCreate, EvolucaoOut, EvolucaoUpdate

router = APIRouter(prefix="/evolucoes", tags=["evolucoes"])


async def _to_out(e: Evolucao, session: SessionDep) -> EvolucaoOut:
    # paciente_id não é denormalizado na evolução → resolvido via sessão
    # (identity-map torna o get barato quando a sessão já foi carregada).
    s = await session.get(Sessao, e.sessao_id)
    return EvolucaoOut(
        id=str(e.id), sessao_id=str(e.sessao_id),
        paciente_id=str(s.paciente_id) if s else None,
        autor_id=str(e.autor_id),
        identificacao=e.identificacao, demanda_objetivos=e.demanda_objetivos,
        evolucao=e.evolucao, encaminhamento=e.encaminhamento,
        assinado_em=e.assinado_em, hash_assinatura=e.hash_assinatura,
        criado_em=e.criado_em, atualizado_em=e.atualizado_em,
    )


def _hash_content(e: Evolucao) -> str:
    payload = "\n".join([
        f"identificacao:{e.identificacao or ''}",
        f"demanda_objetivos:{e.demanda_objetivos or ''}",
        f"evolucao:{e.evolucao or ''}",
        f"encaminhamento:{e.encaminhamento or ''}",
        f"autor:{e.autor_id}",
        f"sessao:{e.sessao_id}",
    ])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@router.post("", response_model=EvolucaoOut, status_code=status.HTTP_201_CREATED)
async def criar(
    body: EvolucaoCreate,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> EvolucaoOut:
    s = await session.get(Sessao, uuid.UUID(body.sessao_id))
    if not s or s.tenant_id != user.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sessão não encontrada")
    e = Evolucao(
        tenant_id=user.tenant_id, sessao_id=s.id, autor_id=user.id,
        identificacao=body.identificacao, demanda_objetivos=body.demanda_objetivos,
        evolucao=body.evolucao, encaminhamento=body.encaminhamento,
    )
    session.add(e)
    await session.commit()
    await session.refresh(e)
    return await _to_out(e, session)


@router.get("/sessao/{sessao_id}", response_model=list[EvolucaoOut])
async def listar_por_sessao(
    sessao_id: str,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> list[EvolucaoOut]:
    q = select(Evolucao).where(
        Evolucao.tenant_id == user.tenant_id,
        Evolucao.sessao_id == uuid.UUID(sessao_id),
    ).order_by(Evolucao.criado_em.asc())
    rows = list((await session.scalars(q)).all())
    return [await _to_out(e, session) for e in rows]


@router.get("/{evolucao_id}", response_model=EvolucaoOut)
async def obter(
    evolucao_id: str,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> EvolucaoOut:
    e = await session.get(Evolucao, uuid.UUID(evolucao_id))
    if not e or e.tenant_id != user.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Evolução não encontrada")
    return await _to_out(e, session)


@router.patch("/{evolucao_id}", response_model=EvolucaoOut)
async def atualizar(
    evolucao_id: str,
    body: EvolucaoUpdate,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> EvolucaoOut:
    e = await session.get(Evolucao, uuid.UUID(evolucao_id))
    if not e or e.tenant_id != user.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Evolução não encontrada")
    if e.assinado_em is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Evolução assinada é imutável")
    for field in ("identificacao", "demanda_objetivos", "evolucao", "encaminhamento"):
        val = getattr(body, field)
        if val is not None:
            setattr(e, field, val)
    await session.commit()
    await session.refresh(e)
    return await _to_out(e, session)


@router.post("/{evolucao_id}/assinar", response_model=EvolucaoOut)
async def assinar(
    evolucao_id: str,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> EvolucaoOut:
    e = await session.get(Evolucao, uuid.UUID(evolucao_id))
    if not e or e.tenant_id != user.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Evolução não encontrada")
    if e.autor_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Só o autor pode assinar")
    if e.assinado_em is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Já assinada")

    e.assinado_em = datetime.now(tz=timezone.utc)
    e.hash_assinatura = _hash_content(e)
    session.add(AuditLog(
        tenant_id=user.tenant_id, user_id=user.id, acao="SIGN",
        entidade="Evolucao", entidade_id=str(e.id),
        meta={"hash": e.hash_assinatura},
    ))

    # Retenção "até assinar": se veio de Scribe, purga a entrada bruta cifrada.
    ger = await session.scalar(
        select(EvolucaoGeracao).where(EvolucaoGeracao.evolucao_id == e.id)
    )
    if ger is not None and ger.entrada_cifrada is not None:
        ger.entrada_cifrada = None
        ger.entrada_purgada_em = e.assinado_em
        session.add(AuditLog(
            tenant_id=user.tenant_id, user_id=user.id, acao="SCRIBE_ENTRADA_PURGED",
            entidade="EvolucaoGeracao", entidade_id=str(ger.id),
            meta={"modo": ger.modo},
        ))

    await session.commit()
    await session.refresh(e)
    return await _to_out(e, session)
