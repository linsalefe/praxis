"""CRUD de Sessao."""
from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select

from app.deps import SessionDep, get_current_user
from app.models.consentimento import Consentimento
from app.models.paciente import Paciente
from app.models.sessao import Sessao
from app.models.user import User
from app.schemas.clinico import (
    SalaStatusOut,
    SessaoAgendaOut,
    SessaoCreate,
    SessaoOut,
    SessaoUpdate,
)
from app.security.crypto import decrypt_str
from app.video.sala import gerar_sala_url

router = APIRouter(prefix="/sessoes", tags=["sessoes"])


def _to_out(s: Sessao) -> SessaoOut:
    return SessaoOut(
        id=str(s.id), paciente_id=str(s.paciente_id), data=s.data,
        modalidade=s.modalidade, status=s.status,
        valor_centavos=s.valor_centavos, sala_url=s.sala_url, criado_em=s.criado_em,
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
    # Valor: usa o informado; se ausente, puxa o padrão do paciente (factual).
    valor = body.valor_centavos if body.valor_centavos is not None else pac.valor_padrao_centavos
    s = Sessao(
        tenant_id=user.tenant_id, paciente_id=pac.id,
        data=body.data, modalidade=body.modalidade, status=body.status,
        valor_centavos=valor,
    )
    session.add(s)
    await session.commit()
    await session.refresh(s)
    return _to_out(s)


@router.get("/agenda", response_model=list[SessaoAgendaOut])
async def agenda(
    de: date,
    ate: date,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> list[SessaoAgendaOut]:
    """Sessões do intervalo [de, ate] (inclusive), todos os status, com nome do
    paciente decifrado — espelha o join do cockpit "Hoje" (inicio.py)."""
    q = (
        select(Sessao, Paciente.nome_cifrado)
        .join(Paciente, Paciente.id == Sessao.paciente_id)
        .where(
            Sessao.tenant_id == user.tenant_id,
            Paciente.deleted_at.is_(None),
            func.date(Sessao.data).between(de, ate),
        )
        .order_by(Sessao.data)
    )
    return [
        SessaoAgendaOut(
            id=str(s.id),
            paciente_id=str(s.paciente_id),
            paciente_nome=decrypt_str(nome_cifrado) or "—",
            data=s.data,
            modalidade=s.modalidade,
            status=s.status,
            valor_centavos=s.valor_centavos,
            sala_url=s.sala_url,
        )
        for s, nome_cifrado in (await session.execute(q)).all()
    ]


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
    if body.valor_centavos is not None:
        s.valor_centavos = body.valor_centavos
    await session.commit()
    await session.refresh(s)
    return _to_out(s)


# --------------------------------------------------------------------------
# Telessessão — sala de vídeo com gate de consentimento (Res. CFP 11/2018)
# --------------------------------------------------------------------------

async def _get_sessao_online(session, user: User, sessao_id: str) -> Sessao:
    try:
        sid = uuid.UUID(sessao_id)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "sessao_id inválido")
    s = await session.get(Sessao, sid)
    if not s or s.tenant_id != user.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sessão não encontrada")
    if s.modalidade != "online":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Sala só existe para sessão online")
    return s


async def _tem_consentimento_tele(session, tenant_id, paciente_id) -> bool:
    c = await session.scalar(
        select(Consentimento).where(
            Consentimento.tenant_id == tenant_id,
            Consentimento.paciente_id == paciente_id,
            Consentimento.tipo == "teleatendimento",
        )
    )
    return c is not None


@router.get("/{sessao_id}/sala", response_model=SalaStatusOut)
async def status_sala(
    sessao_id: str,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> SalaStatusOut:
    """Status para a UI decidir o gate — não gera a sala nem exige consentimento.
    A URL só é revelada quando o consentimento de teleatendimento existe."""
    s = await _get_sessao_online(session, user, sessao_id)
    tem = await _tem_consentimento_tele(session, user.tenant_id, s.paciente_id)
    url = s.sala_url if tem else None
    return SalaStatusOut(
        sessao_id=str(s.id), modalidade=s.modalidade,
        consentimento_teleatendimento=tem,
        sala_url=url, link_paciente=url,
    )


@router.post("/{sessao_id}/sala", response_model=SalaStatusOut)
async def abrir_sala(
    sessao_id: str,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> SalaStatusOut:
    """Gera/obtém a sala (idempotente). Gate CFP: 409 se faltar consentimento."""
    s = await _get_sessao_online(session, user, sessao_id)
    if not await _tem_consentimento_tele(session, user.tenant_id, s.paciente_id):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Consentimento de teleatendimento pendente. Registre o consentimento "
            "(Res. CFP 11/2018) antes de liberar a sala.",
        )
    if not s.sala_url:
        s.sala_url = gerar_sala_url(str(s.id))
        await session.commit()
        await session.refresh(s)
    return SalaStatusOut(
        sessao_id=str(s.id), modalidade=s.modalidade,
        consentimento_teleatendimento=True,
        sala_url=s.sala_url, link_paciente=s.sala_url,
    )
