"""Fluxo de posvenção (fecha Onda 1.1) — cuidado após uma morte por suicídio.

Registro do acolhimento aos enlutados, comunicação segura, articulação de rede,
cuidado com a equipe e acompanhamento do luto. REGISTRO de apoio à decisão
clínica: sem alerta/monitoramento automático.

Escopo tenant + sigilo por profissional (owner vê todos; profissional só os seus),
via `carregar_paciente`. O plano de posvenção e as observações — que contêm PII
de enlutados — são cifrados em repouso.
"""
from __future__ import annotations

import json
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.authz import carregar_paciente
from app.deps import SessionDep, get_current_user
from app.models.posvencao import RegistroPosvencao
from app.models.user import User
from app.risco.posvencao import PASSOS_IDS, definicao
from app.schemas.posvencao import (
    PosvencaoCreate,
    PosvencaoOut,
    PosvencaoResumo,
    PosvencaoUpdate,
)
from app.security.crypto import decrypt_str, encrypt_str

router = APIRouter(tags=["posvencao"])


def _plano_from_cifrado(cifrado: bytes | None) -> dict[str, str]:
    if cifrado is None:
        return {}
    try:
        return json.loads(decrypt_str(cifrado) or "{}")
    except (ValueError, TypeError):
        return {}


def _limpar_plano(plano: dict[str, str] | None) -> dict[str, str]:
    """Só chaves conhecidas do protocolo, com texto não vazio."""
    return {
        k: v.strip()
        for k, v in (plano or {}).items()
        if k in PASSOS_IDS and v and v.strip()
    }


def _to_out(reg: RegistroPosvencao) -> PosvencaoOut:
    plano = _plano_from_cifrado(reg.plano_posvencao_cifrado)
    return PosvencaoOut(
        id=str(reg.id),
        paciente_id=str(reg.paciente_id),
        ocorrido_em=reg.ocorrido_em,
        vinculo_perda=reg.vinculo_perda,
        status=reg.status,
        plano_posvencao=plano,
        observacoes=decrypt_str(reg.observacoes_cifrado),
        passos_preenchidos=len(plano),
        registrado_em=reg.registrado_em,
        criado_em=reg.criado_em,
    )


async def _carregar_registro(session: SessionDep, user: User, registro_id: str) -> RegistroPosvencao:
    try:
        rid = uuid.UUID(registro_id)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "registro inválido")
    reg = await session.get(RegistroPosvencao, rid)
    if reg is None or reg.tenant_id != user.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Registro de posvenção não encontrado")
    # Escopo por profissional: valida acesso ao paciente-âncora.
    await carregar_paciente(session, user, reg.paciente_id)
    return reg


@router.get("/posvencao/definicao")
async def get_definicao(_user: Annotated[User, Depends(get_current_user)]) -> dict:
    """Estrutura do protocolo de posvenção (fonte única do formulário)."""
    return definicao()


@router.post(
    "/pacientes/{paciente_id}/posvencao",
    response_model=PosvencaoOut,
    status_code=status.HTTP_201_CREATED,
)
async def criar(
    paciente_id: str,
    body: PosvencaoCreate,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> PosvencaoOut:
    pac = await carregar_paciente(session, user, paciente_id)

    plano = _limpar_plano(body.plano_posvencao)
    plano_cifrado = encrypt_str(json.dumps(plano, ensure_ascii=False)) if plano else None
    obs_cifrado = encrypt_str(body.observacoes.strip()) if body.observacoes and body.observacoes.strip() else None

    reg = RegistroPosvencao(
        tenant_id=user.tenant_id,
        paciente_id=pac.id,
        criado_por=user.id,
        ocorrido_em=body.ocorrido_em,
        vinculo_perda=body.vinculo_perda,
        status=body.status,
        plano_posvencao_cifrado=plano_cifrado,
        observacoes_cifrado=obs_cifrado,
    )
    session.add(reg)
    await session.commit()
    await session.refresh(reg)
    return _to_out(reg)


@router.get(
    "/pacientes/{paciente_id}/posvencao",
    response_model=list[PosvencaoResumo],
)
async def listar(
    paciente_id: str,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> list[PosvencaoResumo]:
    await carregar_paciente(session, user, paciente_id)
    q = (
        select(RegistroPosvencao)
        .where(
            RegistroPosvencao.tenant_id == user.tenant_id,
            RegistroPosvencao.paciente_id == uuid.UUID(paciente_id),
        )
        .order_by(RegistroPosvencao.ocorrido_em.desc())
    )
    rows = list((await session.scalars(q)).all())
    return [
        PosvencaoResumo(
            id=str(reg.id),
            paciente_id=str(reg.paciente_id),
            ocorrido_em=reg.ocorrido_em,
            vinculo_perda=reg.vinculo_perda,
            status=reg.status,
            passos_preenchidos=len(_plano_from_cifrado(reg.plano_posvencao_cifrado)),
        )
        for reg in rows
    ]


@router.get("/posvencao/{registro_id}", response_model=PosvencaoOut)
async def detalhe(
    registro_id: str,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> PosvencaoOut:
    return _to_out(await _carregar_registro(session, user, registro_id))


@router.patch("/posvencao/{registro_id}", response_model=PosvencaoOut)
async def atualizar(
    registro_id: str,
    body: PosvencaoUpdate,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> PosvencaoOut:
    reg = await _carregar_registro(session, user, registro_id)

    if body.ocorrido_em is not None:
        reg.ocorrido_em = body.ocorrido_em
    if body.vinculo_perda is not None:
        reg.vinculo_perda = body.vinculo_perda
    if body.status is not None:
        reg.status = body.status
    if body.plano_posvencao is not None:
        plano = _limpar_plano(body.plano_posvencao)
        reg.plano_posvencao_cifrado = (
            encrypt_str(json.dumps(plano, ensure_ascii=False)) if plano else None
        )
    if body.observacoes is not None:
        obs = body.observacoes.strip()
        reg.observacoes_cifrado = encrypt_str(obs) if obs else None

    await session.commit()
    await session.refresh(reg)
    return _to_out(reg)
