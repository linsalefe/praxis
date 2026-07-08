"""Laudo de risco psicossocial NR-1 (Onda 3.1).

Documento organizacional (organização/setor), fora do prontuário CFP e sem
consentimento de paciente. Sigilo por profissional pelo `criado_por` (owner vê
todos; profissional vê os seus). Fatores validados contra o checklist NR-1.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.authz import is_owner
from app.deps import SessionDep, get_current_user
from app.laudos.nr1 import FATOR_IDS, definicao
from app.models.laudo_nr1 import LaudoNR1
from app.models.user import User
from app.schemas.laudo_nr1 import (
    FatorAvaliado,
    LaudoNR1Create,
    LaudoNR1Out,
    LaudoNR1Resumo,
    LaudoNR1Update,
)

router = APIRouter(tags=["laudos-nr1"])


async def _carregar_laudo(session, user: User, laudo_id: str) -> LaudoNR1:
    try:
        lid = uuid.UUID(laudo_id)
    except (ValueError, TypeError):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "laudo_id inválido")
    laudo = await session.get(LaudoNR1, lid)
    if laudo is None or laudo.tenant_id != user.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Laudo não encontrado")
    if not is_owner(user) and laudo.criado_por != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Laudo não encontrado")
    return laudo


def _fatores_out(fatores: dict) -> dict[str, FatorAvaliado]:
    out: dict[str, FatorAvaliado] = {}
    for k, v in (fatores or {}).items():
        if k in FATOR_IDS and isinstance(v, dict):
            out[k] = FatorAvaliado(nivel=v.get("nivel", "na"), observacao=v.get("observacao"))
    return out


def _to_out(laudo: LaudoNR1) -> LaudoNR1Out:
    return LaudoNR1Out(
        id=str(laudo.id), organizacao=laudo.organizacao, setor=laudo.setor,
        data=laudo.data, fatores=_fatores_out(laudo.fatores), analise=laudo.analise,
        recomendacoes=laudo.recomendacoes, responsavel=laudo.responsavel,
        status=laudo.status, finalizado_em=laudo.finalizado_em, criado_em=laudo.criado_em,
    )


@router.get("/laudos-nr1/definicao")
async def get_definicao(_user: Annotated[User, Depends(get_current_user)]) -> dict:
    """Checklist de fatores psicossociais NR-1 (fonte única)."""
    return definicao()


@router.post("/laudos-nr1", response_model=LaudoNR1Out, status_code=status.HTTP_201_CREATED)
async def criar(
    body: LaudoNR1Create,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> LaudoNR1Out:
    if not body.organizacao.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Organização é obrigatória")
    laudo = LaudoNR1(
        tenant_id=user.tenant_id, criado_por=user.id,
        organizacao=body.organizacao.strip(), setor=(body.setor or None),
        responsavel=(body.responsavel or None), fatores={},
    )
    session.add(laudo)
    await session.commit()
    await session.refresh(laudo)
    return _to_out(laudo)


@router.get("/laudos-nr1", response_model=list[LaudoNR1Resumo])
async def listar(
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> list[LaudoNR1Resumo]:
    q = select(LaudoNR1).where(LaudoNR1.tenant_id == user.tenant_id)
    if not is_owner(user):
        q = q.where(LaudoNR1.criado_por == user.id)
    q = q.order_by(LaudoNR1.data.desc())
    laudos = list((await session.scalars(q)).all())
    return [
        LaudoNR1Resumo(
            id=str(l.id), organizacao=l.organizacao, setor=l.setor, data=l.data,
            status=l.status,
            fatores_alto=sum(1 for v in (l.fatores or {}).values()
                             if isinstance(v, dict) and v.get("nivel") == "alto"),
        )
        for l in laudos
    ]


@router.get("/laudos-nr1/{laudo_id}", response_model=LaudoNR1Out)
async def detalhe(
    laudo_id: str,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> LaudoNR1Out:
    return _to_out(await _carregar_laudo(session, user, laudo_id))


@router.patch("/laudos-nr1/{laudo_id}", response_model=LaudoNR1Out)
async def atualizar(
    laudo_id: str,
    body: LaudoNR1Update,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> LaudoNR1Out:
    laudo = await _carregar_laudo(session, user, laudo_id)
    if laudo.status == "finalizado":
        raise HTTPException(status.HTTP_409_CONFLICT, "Laudo finalizado não pode ser editado")
    if body.organizacao is not None:
        if not body.organizacao.strip():
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Organização não pode ser vazia")
        laudo.organizacao = body.organizacao.strip()
    if body.setor is not None:
        laudo.setor = body.setor or None
    if body.responsavel is not None:
        laudo.responsavel = body.responsavel or None
    if body.analise is not None:
        laudo.analise = body.analise or None
    if body.recomendacoes is not None:
        laudo.recomendacoes = body.recomendacoes or None
    if body.fatores is not None:
        # Só fatores conhecidos; nível já validado pelo schema.
        laudo.fatores = {
            k: {"nivel": v.nivel, "observacao": (v.observacao or None)}
            for k, v in body.fatores.items() if k in FATOR_IDS
        }
    await session.commit()
    await session.refresh(laudo)
    return _to_out(laudo)


@router.post("/laudos-nr1/{laudo_id}/finalizar", response_model=LaudoNR1Out)
async def finalizar(
    laudo_id: str,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> LaudoNR1Out:
    laudo = await _carregar_laudo(session, user, laudo_id)
    if laudo.status == "finalizado":
        return _to_out(laudo)
    laudo.status = "finalizado"
    laudo.finalizado_em = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(laudo)
    return _to_out(laudo)


@router.delete("/laudos-nr1/{laudo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remover(
    laudo_id: str,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> None:
    laudo = await _carregar_laudo(session, user, laudo_id)
    await session.delete(laudo)
    await session.commit()
