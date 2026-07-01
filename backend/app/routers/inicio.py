"""Cockpit clínico "Hoje" — agregação read-only de pendências acionáveis.

Aditivo: apenas lê tabelas existentes, num único round-trip. Isolamento por
tenant sempre; pendências com autoria (evolução/documento/instrumento) também
por autor_id ("minhas pendências"). Sessões não têm autor → escopo por tenant.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select

from app.deps import SessionDep, get_current_user
from app.models.documento import DocumentoCFP
from app.models.evolucao import Evolucao
from app.models.instrumentos import Instrumento, RespostaInstrumento
from app.models.paciente import Paciente
from app.models.sessao import Sessao
from app.models.user import User
from app.schemas.inicio import (
    Contadores,
    DocumentoRascunho,
    EvolucaoRascunho,
    InstrumentoPendente,
    PendenciasOut,
    SessaoHoje,
)
from app.security.crypto import decrypt_str

router = APIRouter(prefix="/inicio", tags=["inicio"])

LIMITE = 20


@router.get("/pendencias", response_model=PendenciasOut)
async def pendencias(
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> PendenciasOut:
    tid = user.tenant_id
    me = user.id

    def nome(cifrado: bytes | None) -> str:
        return decrypt_str(cifrado) or "—"

    # --- Sessões de hoje (escopo: tenant; Sessao não tem autor_id) ---
    q_sessoes = (
        select(Sessao, Paciente.nome_cifrado)
        .join(Paciente, Paciente.id == Sessao.paciente_id)
        .where(
            Sessao.tenant_id == tid,
            Paciente.deleted_at.is_(None),
            func.date(Sessao.data) == func.current_date(),
            Sessao.status == "agendada",
        )
        .order_by(Sessao.data)
    )
    sessoes_hoje = [
        SessaoHoje(
            sessao_id=str(s.id),
            paciente_id=str(s.paciente_id),
            paciente_nome=nome(nome_cifrado),
            data=s.data,
            modalidade=s.modalidade,
            status=s.status,
        )
        for s, nome_cifrado in (await session.execute(q_sessoes)).all()
    ]

    # --- Evoluções em rascunho (assinado_em IS NULL), minhas ---
    q_evol = (
        select(Evolucao, Sessao.paciente_id, Paciente.nome_cifrado)
        .join(Sessao, Sessao.id == Evolucao.sessao_id)
        .join(Paciente, Paciente.id == Sessao.paciente_id)
        .where(
            Evolucao.tenant_id == tid,
            Evolucao.autor_id == me,
            Evolucao.assinado_em.is_(None),
            Paciente.deleted_at.is_(None),
        )
        .order_by(Evolucao.criado_em.desc())
        .limit(LIMITE)
    )
    evolucoes_rascunho = [
        EvolucaoRascunho(
            evolucao_id=str(e.id),
            sessao_id=str(e.sessao_id),
            paciente_id=str(pac_id),
            paciente_nome=nome(nome_cifrado),
            criado_em=e.criado_em,
        )
        for e, pac_id, nome_cifrado in (await session.execute(q_evol)).all()
    ]

    # --- Documentos CFP em rascunho, meus ---
    q_docs = (
        select(DocumentoCFP, Paciente.nome_cifrado)
        .join(Paciente, Paciente.id == DocumentoCFP.paciente_id)
        .where(
            DocumentoCFP.tenant_id == tid,
            DocumentoCFP.autor_id == me,
            DocumentoCFP.status == "rascunho",
            Paciente.deleted_at.is_(None),
        )
        .order_by(DocumentoCFP.criado_em.desc())
        .limit(LIMITE)
    )
    documentos_rascunho = [
        DocumentoRascunho(
            documento_id=str(d.id),
            paciente_id=str(d.paciente_id),
            paciente_nome=nome(nome_cifrado),
            tipo=d.tipo,
            finalidade=d.finalidade,
            criado_em=d.criado_em,
        )
        for d, nome_cifrado in (await session.execute(q_docs)).all()
    ]

    # --- Instrumentos aguardando interpretação (saida_gerada_em IS NULL), meus ---
    q_instr = (
        select(RespostaInstrumento, Instrumento.titulo, Paciente.nome_cifrado)
        .join(Instrumento, Instrumento.id == RespostaInstrumento.instrumento_id)
        .join(Paciente, Paciente.id == RespostaInstrumento.paciente_id)
        .where(
            RespostaInstrumento.tenant_id == tid,
            RespostaInstrumento.autor_id == me,
            RespostaInstrumento.saida_gerada_em.is_(None),
            Paciente.deleted_at.is_(None),
        )
        .order_by(RespostaInstrumento.criado_em.desc())
        .limit(LIMITE)
    )
    instrumentos_pendentes = [
        InstrumentoPendente(
            resposta_id=str(r.id),
            paciente_id=str(r.paciente_id),
            paciente_nome=nome(nome_cifrado),
            instrumento_titulo=titulo,
            criado_em=r.criado_em,
        )
        for r, titulo, nome_cifrado in (await session.execute(q_instr)).all()
    ]

    # --- Contadores reais (independentes do LIMIT das listas) ---
    async def contar(stmt) -> int:
        return int((await session.scalar(stmt)) or 0)

    c_sessoes = await contar(
        select(func.count())
        .select_from(Sessao)
        .join(Paciente, Paciente.id == Sessao.paciente_id)
        .where(
            Sessao.tenant_id == tid,
            Paciente.deleted_at.is_(None),
            func.date(Sessao.data) == func.current_date(),
            Sessao.status == "agendada",
        )
    )
    c_evol = await contar(
        select(func.count())
        .select_from(Evolucao)
        .join(Sessao, Sessao.id == Evolucao.sessao_id)
        .join(Paciente, Paciente.id == Sessao.paciente_id)
        .where(
            Evolucao.tenant_id == tid,
            Evolucao.autor_id == me,
            Evolucao.assinado_em.is_(None),
            Paciente.deleted_at.is_(None),
        )
    )
    c_docs = await contar(
        select(func.count())
        .select_from(DocumentoCFP)
        .join(Paciente, Paciente.id == DocumentoCFP.paciente_id)
        .where(
            DocumentoCFP.tenant_id == tid,
            DocumentoCFP.autor_id == me,
            DocumentoCFP.status == "rascunho",
            Paciente.deleted_at.is_(None),
        )
    )
    c_instr = await contar(
        select(func.count())
        .select_from(RespostaInstrumento)
        .join(Paciente, Paciente.id == RespostaInstrumento.paciente_id)
        .where(
            RespostaInstrumento.tenant_id == tid,
            RespostaInstrumento.autor_id == me,
            RespostaInstrumento.saida_gerada_em.is_(None),
            Paciente.deleted_at.is_(None),
        )
    )

    return PendenciasOut(
        sessoes_hoje=sessoes_hoje,
        evolucoes_rascunho=evolucoes_rascunho,
        documentos_rascunho=documentos_rascunho,
        instrumentos_pendentes=instrumentos_pendentes,
        contadores=Contadores(
            sessoes_hoje=c_sessoes,
            evolucoes_rascunho=c_evol,
            documentos_rascunho=c_docs,
            instrumentos_pendentes=c_instr,
        ),
    )
