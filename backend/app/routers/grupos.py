"""Encontros de grupo/oficina/assembleia (Onda 2.2).

Um encontro agrega participantes (pacientes registrados e/ou pessoas em texto
livre, com nome cifrado). Sigilo por profissional pelo `criado_por`: owner vê
todos os encontros do tenant; profissional vê os seus. Pacientes adicionados
como participantes passam por `carregar_paciente` (um profissional só adiciona
os seus pacientes).
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select

from app.authz import carregar_paciente, is_owner
from app.deps import SessionDep, get_current_user
from app.models.grupo import EncontroGrupo, ParticipanteEncontro
from app.models.paciente import Paciente
from app.models.user import User
from app.schemas.grupo import (
    EncontroCreate,
    EncontroOut,
    EncontroResumo,
    EncontroUpdate,
    ParticipanteIn,
    ParticipanteOut,
)
from app.security.crypto import decrypt_str, encrypt_str

router = APIRouter(prefix="/grupos", tags=["grupos"])


async def _carregar_encontro(session, user: User, encontro_id: str) -> EncontroGrupo:
    try:
        eid = uuid.UUID(encontro_id)
    except (ValueError, TypeError):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "encontro_id inválido")
    enc = await session.get(EncontroGrupo, eid)
    if enc is None or enc.tenant_id != user.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Encontro não encontrado")
    # Sigilo por profissional: só o dono (ou owner) acessa.
    if not is_owner(user) and enc.criado_por != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Encontro não encontrado")
    return enc


async def _nome_pacientes(session, tenant_id, ids: set[uuid.UUID]) -> dict[uuid.UUID, str]:
    if not ids:
        return {}
    rows = (await session.execute(
        select(Paciente.id, Paciente.nome_cifrado).where(
            Paciente.tenant_id == tenant_id, Paciente.id.in_(ids)
        )
    )).all()
    return {pid: (decrypt_str(nc) or "—") for pid, nc in rows}


async def _participantes_out(session, user: User, encontro_id: uuid.UUID) -> list[ParticipanteOut]:
    parts = list((await session.scalars(
        select(ParticipanteEncontro)
        .where(ParticipanteEncontro.encontro_id == encontro_id)
        .order_by(ParticipanteEncontro.criado_em)
    )).all())
    nomes = await _nome_pacientes(
        session, user.tenant_id, {p.paciente_id for p in parts if p.paciente_id}
    )
    out: list[ParticipanteOut] = []
    for p in parts:
        if p.paciente_id:
            nome = nomes.get(p.paciente_id, "—")
        else:
            nome = decrypt_str(p.nome_livre_cifrado) or "—"
        out.append(ParticipanteOut(
            id=str(p.id), paciente_id=str(p.paciente_id) if p.paciente_id else None,
            nome=nome, e_paciente=p.paciente_id is not None, presente=p.presente,
        ))
    return out


async def _inserir_participante(session, user: User, encontro_id: uuid.UUID, p: ParticipanteIn) -> None:
    paciente_id = None
    nome_cifrado = None
    if p.paciente_id:
        pac = await carregar_paciente(session, user, p.paciente_id)  # valida sigilo
        paciente_id = pac.id
    elif p.nome_livre and p.nome_livre.strip():
        nome_cifrado = encrypt_str(p.nome_livre.strip())
    else:
        return  # participante vazio: ignora
    session.add(ParticipanteEncontro(
        tenant_id=user.tenant_id, encontro_id=encontro_id,
        paciente_id=paciente_id, nome_livre_cifrado=nome_cifrado, presente=p.presente,
    ))


@router.post("", response_model=EncontroOut, status_code=status.HTTP_201_CREATED)
async def criar(
    body: EncontroCreate,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> EncontroOut:
    enc = EncontroGrupo(
        tenant_id=user.tenant_id, criado_por=user.id, tipo=body.tipo,
        titulo=body.titulo, data=body.data, local=body.local,
        tema=body.tema, registro=body.registro,
    )
    session.add(enc)
    await session.flush()
    for p in body.participantes:
        await _inserir_participante(session, user, enc.id, p)
    await session.commit()
    await session.refresh(enc)
    return EncontroOut(
        id=str(enc.id), tipo=enc.tipo, titulo=enc.titulo, data=enc.data,
        local=enc.local, tema=enc.tema, registro=enc.registro, criado_em=enc.criado_em,
        participantes=await _participantes_out(session, user, enc.id),
    )


@router.get("", response_model=list[EncontroResumo])
async def listar(
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> list[EncontroResumo]:
    q = select(EncontroGrupo).where(EncontroGrupo.tenant_id == user.tenant_id)
    if not is_owner(user):
        q = q.where(EncontroGrupo.criado_por == user.id)
    q = q.order_by(EncontroGrupo.data.desc())
    encontros = list((await session.scalars(q)).all())
    out: list[EncontroResumo] = []
    for e in encontros:
        total = await session.scalar(
            select(func.count()).select_from(ParticipanteEncontro).where(ParticipanteEncontro.encontro_id == e.id)
        ) or 0
        presentes = await session.scalar(
            select(func.count()).select_from(ParticipanteEncontro).where(
                ParticipanteEncontro.encontro_id == e.id, ParticipanteEncontro.presente.is_(True)
            )
        ) or 0
        out.append(EncontroResumo(
            id=str(e.id), tipo=e.tipo, titulo=e.titulo, data=e.data, local=e.local,
            total_participantes=total, presentes=presentes,
        ))
    return out


@router.get("/{encontro_id}", response_model=EncontroOut)
async def detalhe(
    encontro_id: str,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> EncontroOut:
    enc = await _carregar_encontro(session, user, encontro_id)
    return EncontroOut(
        id=str(enc.id), tipo=enc.tipo, titulo=enc.titulo, data=enc.data,
        local=enc.local, tema=enc.tema, registro=enc.registro, criado_em=enc.criado_em,
        participantes=await _participantes_out(session, user, enc.id),
    )


@router.patch("/{encontro_id}", response_model=EncontroOut)
async def atualizar(
    encontro_id: str,
    body: EncontroUpdate,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> EncontroOut:
    enc = await _carregar_encontro(session, user, encontro_id)
    for campo in ("tipo", "titulo", "data", "local", "tema", "registro"):
        val = getattr(body, campo)
        if val is not None:
            setattr(enc, campo, val)
    await session.commit()
    await session.refresh(enc)
    return EncontroOut(
        id=str(enc.id), tipo=enc.tipo, titulo=enc.titulo, data=enc.data,
        local=enc.local, tema=enc.tema, registro=enc.registro, criado_em=enc.criado_em,
        participantes=await _participantes_out(session, user, enc.id),
    )


@router.post("/{encontro_id}/participantes", response_model=EncontroOut, status_code=status.HTTP_201_CREATED)
async def adicionar_participante(
    encontro_id: str,
    body: ParticipanteIn,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> EncontroOut:
    enc = await _carregar_encontro(session, user, encontro_id)
    await _inserir_participante(session, user, enc.id, body)
    await session.commit()
    return EncontroOut(
        id=str(enc.id), tipo=enc.tipo, titulo=enc.titulo, data=enc.data,
        local=enc.local, tema=enc.tema, registro=enc.registro, criado_em=enc.criado_em,
        participantes=await _participantes_out(session, user, enc.id),
    )


@router.delete("/{encontro_id}/participantes/{participante_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remover_participante(
    encontro_id: str,
    participante_id: str,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> None:
    enc = await _carregar_encontro(session, user, encontro_id)
    try:
        pid = uuid.UUID(participante_id)
    except (ValueError, TypeError):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "participante_id inválido")
    part = await session.get(ParticipanteEncontro, pid)
    if part is None or part.encontro_id != enc.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Participante não encontrado")
    await session.delete(part)
    await session.commit()
