"""Casos e PTS (espinha Caso/PTS, Onda 1.2).

`Caso` agrega o cuidado de um paciente; `PtsVersao` é o Projeto Terapêutico
Singular versionado (cada save = nova versão; a atual é a de maior número).

Escopo tenant + sigilo por profissional: o acesso ao caso é validado pelo acesso
ao paciente dono (`carregar_paciente`), então owner vê todos e profissional só os
seus. Aditivo: o consultório pode ignorar casos; nada quebra sem eles.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select

from app.authz import carregar_paciente
from app.casos.pts import PTS_SECAO_IDS, definicao
from app.deps import SessionDep, get_current_user
from app.models.caso import Caso, PtsVersao
from app.models.rede import MembroRede
from app.models.user import User
from app.schemas.caso import (
    CasoCreate,
    CasoOut,
    CasoResumo,
    CasoUpdate,
    MembroRedeCreate,
    MembroRedeOut,
    MembroRedeUpdate,
    PtsSalvar,
    PtsVersaoOut,
)
from app.security.crypto import decrypt_str, encrypt_str

router = APIRouter(tags=["casos"])


async def _carregar_caso(session, user: User, caso_id: str) -> Caso:
    """Carrega um caso do tenant, validando o sigilo pelo paciente dono."""
    try:
        cid = uuid.UUID(caso_id)
    except (ValueError, TypeError):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "caso_id inválido")
    caso = await session.get(Caso, cid)
    if caso is None or caso.tenant_id != user.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Caso não encontrado")
    # Escopo por profissional: valida acesso ao paciente dono do caso (pode 404).
    await carregar_paciente(session, user, caso.paciente_id)
    return caso


async def _pts_atual(session, caso_id: uuid.UUID) -> PtsVersao | None:
    return await session.scalar(
        select(PtsVersao).where(PtsVersao.caso_id == caso_id).order_by(PtsVersao.versao.desc()).limit(1)
    )


def _pts_out(p: PtsVersao) -> PtsVersaoOut:
    return PtsVersaoOut(
        id=str(p.id), caso_id=str(p.caso_id), versao=p.versao,
        conteudo=p.conteudo or {}, criado_por=str(p.criado_por), criado_em=p.criado_em,
    )


def _caso_out(caso: Caso, pts: PtsVersao | None) -> CasoOut:
    return CasoOut(
        id=str(caso.id), paciente_id=str(caso.paciente_id), titulo=caso.titulo,
        status=caso.status, aberto_em=caso.aberto_em, encerrado_em=caso.encerrado_em,
        criado_em=caso.criado_em, pts_atual=_pts_out(pts) if pts else None,
    )


@router.get("/casos/pts/definicao")
async def get_definicao(_user: Annotated[User, Depends(get_current_user)]) -> dict:
    """Seções do PTS (fonte única do formulário)."""
    return definicao()


@router.post(
    "/pacientes/{paciente_id}/casos",
    response_model=CasoOut,
    status_code=status.HTTP_201_CREATED,
)
async def criar_caso(
    paciente_id: str,
    body: CasoCreate,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> CasoOut:
    pac = await carregar_paciente(session, user, paciente_id)
    caso = Caso(
        tenant_id=user.tenant_id, paciente_id=pac.id, criado_por=user.id,
        titulo=(body.titulo or None),
    )
    session.add(caso)
    await session.commit()
    await session.refresh(caso)
    return _caso_out(caso, None)


@router.get("/pacientes/{paciente_id}/casos", response_model=list[CasoResumo])
async def listar_casos(
    paciente_id: str,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> list[CasoResumo]:
    await carregar_paciente(session, user, paciente_id)
    q = (
        select(Caso)
        .where(Caso.tenant_id == user.tenant_id, Caso.paciente_id == uuid.UUID(paciente_id))
        .order_by(Caso.aberto_em.desc())
    )
    casos = list((await session.scalars(q)).all())
    out: list[CasoResumo] = []
    for c in casos:
        vmax = await session.scalar(
            select(func.max(PtsVersao.versao)).where(PtsVersao.caso_id == c.id)
        )
        out.append(CasoResumo(
            id=str(c.id), paciente_id=str(c.paciente_id), titulo=c.titulo,
            status=c.status, aberto_em=c.aberto_em, pts_versao_atual=vmax,
        ))
    return out


@router.get("/casos/{caso_id}", response_model=CasoOut)
async def detalhe_caso(
    caso_id: str,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> CasoOut:
    caso = await _carregar_caso(session, user, caso_id)
    return _caso_out(caso, await _pts_atual(session, caso.id))


@router.patch("/casos/{caso_id}", response_model=CasoOut)
async def atualizar_caso(
    caso_id: str,
    body: CasoUpdate,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> CasoOut:
    caso = await _carregar_caso(session, user, caso_id)
    if body.titulo is not None:
        caso.titulo = body.titulo or None
    if body.status is not None:
        if body.status not in ("ativo", "encerrado"):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "status inválido")
        caso.status = body.status
        caso.encerrado_em = datetime.now(timezone.utc) if body.status == "encerrado" else None
    await session.commit()
    await session.refresh(caso)
    return _caso_out(caso, await _pts_atual(session, caso.id))


@router.post("/casos/{caso_id}/pts", response_model=PtsVersaoOut, status_code=status.HTTP_201_CREATED)
async def salvar_pts(
    caso_id: str,
    body: PtsSalvar,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> PtsVersaoOut:
    """Cria uma nova versão do PTS (imutável). Só chaves de seção conhecidas."""
    caso = await _carregar_caso(session, user, caso_id)
    conteudo = {
        k: v.strip()
        for k, v in (body.conteudo or {}).items()
        if k in PTS_SECAO_IDS and v and v.strip()
    }
    vmax = await session.scalar(select(func.max(PtsVersao.versao)).where(PtsVersao.caso_id == caso.id))
    pts = PtsVersao(
        tenant_id=user.tenant_id, caso_id=caso.id, versao=(vmax or 0) + 1,
        conteudo=conteudo, criado_por=user.id,
    )
    session.add(pts)
    await session.commit()
    await session.refresh(pts)
    return _pts_out(pts)


@router.get("/casos/{caso_id}/pts", response_model=list[PtsVersaoOut])
async def historico_pts(
    caso_id: str,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> list[PtsVersaoOut]:
    caso = await _carregar_caso(session, user, caso_id)
    q = select(PtsVersao).where(PtsVersao.caso_id == caso.id).order_by(PtsVersao.versao.desc())
    return [_pts_out(p) for p in (await session.scalars(q)).all()]


# --------------------------------------------------------------------------
# Rede de apoio (genograma/ecomapa) — Onda 2.3
# --------------------------------------------------------------------------

def _membro_out(m: MembroRede) -> MembroRedeOut:
    return MembroRedeOut(
        id=str(m.id), caso_id=str(m.caso_id), nome=decrypt_str(m.nome_cifrado) or "—",
        papel=m.papel, tipo_vinculo=m.tipo_vinculo, forca_vinculo=m.forca_vinculo,
        observacoes=m.observacoes,
    )


async def _carregar_membro(session, caso: Caso, membro_id: str) -> MembroRede:
    try:
        mid = uuid.UUID(membro_id)
    except (ValueError, TypeError):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "membro_id inválido")
    m = await session.get(MembroRede, mid)
    if m is None or m.caso_id != caso.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Membro não encontrado")
    return m


@router.get("/casos/{caso_id}/rede", response_model=list[MembroRedeOut])
async def listar_rede(
    caso_id: str,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> list[MembroRedeOut]:
    caso = await _carregar_caso(session, user, caso_id)
    q = select(MembroRede).where(MembroRede.caso_id == caso.id).order_by(MembroRede.criado_em)
    return [_membro_out(m) for m in (await session.scalars(q)).all()]


@router.post("/casos/{caso_id}/rede", response_model=MembroRedeOut, status_code=status.HTTP_201_CREATED)
async def adicionar_membro(
    caso_id: str,
    body: MembroRedeCreate,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> MembroRedeOut:
    caso = await _carregar_caso(session, user, caso_id)
    if not body.nome.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Nome é obrigatório")
    m = MembroRede(
        tenant_id=user.tenant_id, caso_id=caso.id, criado_por=user.id,
        nome_cifrado=encrypt_str(body.nome.strip()), papel=(body.papel or None),
        tipo_vinculo=body.tipo_vinculo, forca_vinculo=body.forca_vinculo,
        observacoes=(body.observacoes or None),
    )
    session.add(m)
    await session.commit()
    await session.refresh(m)
    return _membro_out(m)


@router.patch("/casos/{caso_id}/rede/{membro_id}", response_model=MembroRedeOut)
async def atualizar_membro(
    caso_id: str,
    membro_id: str,
    body: MembroRedeUpdate,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> MembroRedeOut:
    caso = await _carregar_caso(session, user, caso_id)
    m = await _carregar_membro(session, caso, membro_id)
    if body.nome is not None:
        if not body.nome.strip():
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Nome não pode ser vazio")
        m.nome_cifrado = encrypt_str(body.nome.strip())
    if body.papel is not None:
        m.papel = body.papel or None
    if body.tipo_vinculo is not None:
        m.tipo_vinculo = body.tipo_vinculo
    if body.forca_vinculo is not None:
        m.forca_vinculo = body.forca_vinculo
    if body.observacoes is not None:
        m.observacoes = body.observacoes or None
    await session.commit()
    await session.refresh(m)
    return _membro_out(m)


@router.delete("/casos/{caso_id}/rede/{membro_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remover_membro(
    caso_id: str,
    membro_id: str,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> None:
    caso = await _carregar_caso(session, user, caso_id)
    m = await _carregar_membro(session, caso, membro_id)
    await session.delete(m)
    await session.commit()
