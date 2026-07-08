"""Módulo de risco — avaliação de risco de suicídio/autolesão (Onda 1.1).

Rastreio C-SSRS + Plano de Segurança (Stanley-Brown). REGISTRO de apoio à decisão
clínica: o nível é derivado no servidor (fonte única: app/risco/scoring.py) e
nunca confiado no cliente; não há alerta/monitoramento automático.

Escopo tenant + sigilo por profissional (owner vê todos; profissional só os seus),
via `carregar_paciente`. Plano de Segurança e observações são cifrados em repouso.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.authz import carregar_paciente
from app.deps import SessionDep, get_current_user
from app.models.risco import AvaliacaoRisco
from app.models.user import User
from app.risco.cssrs import PLANO_SEGURANCA_IDS, definicao
from app.risco.scoring import estratificar
from app.schemas.risco import (
    AvaliacaoRiscoCreate,
    AvaliacaoRiscoOut,
    AvaliacaoRiscoResumo,
    RiscoAtualOut,
)
from app.security.crypto import decrypt_str, encrypt_str

router = APIRouter(tags=["risco"])


def _plano_from_cifrado(cifrado: bytes | None) -> dict[str, str]:
    if cifrado is None:
        return {}
    try:
        return json.loads(decrypt_str(cifrado) or "{}")
    except (ValueError, TypeError):
        return {}


def _to_out(av: AvaliacaoRisco) -> AvaliacaoRiscoOut:
    strat = estratificar(av.cssrs or {})
    return AvaliacaoRiscoOut(
        id=str(av.id),
        paciente_id=str(av.paciente_id),
        avaliado_em=av.avaliado_em,
        nivel_risco=av.nivel_risco,
        gatilhos=strat["gatilhos"],
        recomendacao=strat["recomendacao"],
        cssrs=av.cssrs or {},
        plano_seguranca=_plano_from_cifrado(av.plano_seguranca_cifrado),
        observacoes=decrypt_str(av.observacoes_cifrado),
        criado_em=av.criado_em,
    )


@router.get("/risco/definicao")
async def get_definicao(_user: Annotated[User, Depends(get_current_user)]) -> dict:
    """Estrutura do rastreio C-SSRS + Plano de Segurança (fonte única do form)."""
    return definicao()


@router.post(
    "/pacientes/{paciente_id}/avaliacoes-risco",
    response_model=AvaliacaoRiscoOut,
    status_code=status.HTTP_201_CREATED,
)
async def criar(
    paciente_id: str,
    body: AvaliacaoRiscoCreate,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> AvaliacaoRiscoOut:
    pac = await carregar_paciente(session, user, paciente_id)

    cssrs = body.cssrs.model_dump()
    nivel = estratificar(cssrs)["nivel"]  # derivado no servidor — nunca do cliente

    # Plano de Segurança: só chaves conhecidas, textos não vazios.
    plano = {
        k: v.strip()
        for k, v in (body.plano_seguranca or {}).items()
        if k in PLANO_SEGURANCA_IDS and v and v.strip()
    }
    plano_cifrado = encrypt_str(json.dumps(plano, ensure_ascii=False)) if plano else None
    obs_cifrado = encrypt_str(body.observacoes.strip()) if body.observacoes and body.observacoes.strip() else None

    avaliado_em = body.avaliado_em or datetime.now(timezone.utc)

    av = AvaliacaoRisco(
        tenant_id=user.tenant_id,
        paciente_id=pac.id,
        criado_por=user.id,
        avaliado_em=avaliado_em,
        cssrs=cssrs,
        nivel_risco=nivel,
        plano_seguranca_cifrado=plano_cifrado,
        observacoes_cifrado=obs_cifrado,
    )
    session.add(av)
    await session.commit()
    await session.refresh(av)
    return _to_out(av)


@router.get(
    "/pacientes/{paciente_id}/avaliacoes-risco",
    response_model=list[AvaliacaoRiscoResumo],
)
async def listar(
    paciente_id: str,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> list[AvaliacaoRiscoResumo]:
    await carregar_paciente(session, user, paciente_id)
    q = (
        select(AvaliacaoRisco)
        .where(
            AvaliacaoRisco.tenant_id == user.tenant_id,
            AvaliacaoRisco.paciente_id == uuid.UUID(paciente_id),
        )
        .order_by(AvaliacaoRisco.avaliado_em.desc())
    )
    rows = list((await session.scalars(q)).all())
    return [
        AvaliacaoRiscoResumo(
            id=str(av.id),
            paciente_id=str(av.paciente_id),
            avaliado_em=av.avaliado_em,
            nivel_risco=av.nivel_risco,
            gatilhos=estratificar(av.cssrs or {})["gatilhos"],
        )
        for av in rows
    ]


@router.get("/pacientes/{paciente_id}/risco-atual", response_model=RiscoAtualOut)
async def risco_atual(
    paciente_id: str,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> RiscoAtualOut:
    """Bandeira de risco do prontuário: a avaliação mais recente, se houver."""
    await carregar_paciente(session, user, paciente_id)
    av = await session.scalar(
        select(AvaliacaoRisco)
        .where(
            AvaliacaoRisco.tenant_id == user.tenant_id,
            AvaliacaoRisco.paciente_id == uuid.UUID(paciente_id),
        )
        .order_by(AvaliacaoRisco.avaliado_em.desc())
        .limit(1)
    )
    if av is None:
        return RiscoAtualOut(tem_avaliacao=False)
    return RiscoAtualOut(
        tem_avaliacao=True,
        nivel_risco=av.nivel_risco,
        avaliado_em=av.avaliado_em,
        avaliacao_id=str(av.id),
    )


@router.get("/avaliacoes-risco/{avaliacao_id}", response_model=AvaliacaoRiscoOut)
async def detalhe(
    avaliacao_id: str,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> AvaliacaoRiscoOut:
    try:
        aid = uuid.UUID(avaliacao_id)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "avaliacao_id inválido")
    av = await session.get(AvaliacaoRisco, aid)
    if av is None or av.tenant_id != user.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Avaliação não encontrada")
    # Escopo por profissional: valida acesso ao paciente dono da avaliação.
    await carregar_paciente(session, user, av.paciente_id)
    return _to_out(av)
