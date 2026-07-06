"""Acompanhamento longitudinal por-paciente — agregação read-only, factual.

Aditivo: só lê tabelas existentes (sessões, evoluções, respostas de instrumento,
documentos). Escopo tenant + paciente (o caso inteiro, não filtrado por autor).
Escores vêm de `pontuar_likert` (fonte única) — nada é recalculado nem fabricado.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select

from app.authz import carregar_paciente
from app.deps import SessionDep, get_current_user
from app.instrumentos.scoring import pontuar_likert
from app.models.documento import DocumentoCFP
from app.models.evolucao import Evolucao
from app.models.instrumentos import Instrumento, RespostaInstrumento
from app.models.paciente import Paciente
from app.models.sessao import Sessao
from app.models.user import User
from app.schemas.longitudinal import (
    Adesao,
    EventoTimeline,
    EvolucoesResumo,
    FaixaDef,
    PontoSerie,
    ResumoOut,
    SerieTrajetoria,
    SessoesResumo,
    TimelineOut,
    TrajetoriaOut,
)

router = APIRouter(tags=["longitudinal"])


async def _assert_paciente(session, user: User, paciente_id: str) -> Paciente:
    # Escopo por profissional (P1): owner vê todos; profissional só os seus.
    return await carregar_paciente(session, user, paciente_id)


def _escore_max(definicao: dict[str, Any], subescala: dict[str, Any] | None = None) -> int:
    """Máximo teórico do escore (para o eixo-Y honesto), das opções/itens declarados."""
    opcoes = definicao.get("opcoes", []) or []
    op_max = max((o.get("valor", 0) for o in opcoes), default=0)
    if subescala is not None:
        n = len(subescala.get("itens", []))
        return n * op_max * subescala.get("multiplicador", 1)
    n = len(definicao.get("itens", []) or [])
    base = n * op_max
    transf = definicao.get("transformacao")
    if transf and transf.get("tipo") == "x4":
        return base * 4
    return base


# --------------------------------------------------------------------------
# Linha do tempo unificada
# --------------------------------------------------------------------------

@router.get("/pacientes/{paciente_id}/timeline", response_model=TimelineOut)
async def timeline(
    paciente_id: str,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> TimelineOut:
    pac = await _assert_paciente(session, user, paciente_id)
    tid = user.tenant_id
    eventos: list[EventoTimeline] = []

    # Sessões
    q_ses = select(Sessao).where(Sessao.tenant_id == tid, Sessao.paciente_id == pac.id)
    for s in (await session.scalars(q_ses)).all():
        eventos.append(EventoTimeline(
            data=s.data, tipo_evento="sessao", ref_id=str(s.id),
            titulo=f"Sessão ({s.modalidade})", meta={"status": s.status},
        ))

    # Evoluções (paciente via sessão)
    q_evo = (
        select(Evolucao)
        .join(Sessao, Sessao.id == Evolucao.sessao_id)
        .where(Evolucao.tenant_id == tid, Sessao.paciente_id == pac.id)
    )
    for e in (await session.scalars(q_evo)).all():
        assinada = e.assinado_em is not None
        eventos.append(EventoTimeline(
            data=e.criado_em, tipo_evento="evolucao", ref_id=str(e.id),
            titulo="Evolução " + ("assinada" if assinada else "rascunho"),
            meta={"assinada": assinada, "sessao_id": str(e.sessao_id)},
        ))

    # Instrumentos (escore factual quando likert_sum completo)
    q_ins = (
        select(RespostaInstrumento, Instrumento)
        .join(Instrumento, Instrumento.id == RespostaInstrumento.instrumento_id)
        .where(RespostaInstrumento.tenant_id == tid, RespostaInstrumento.paciente_id == pac.id)
    )
    for r, instr in (await session.execute(q_ins)).all():
        meta: dict[str, Any] = {"status": r.status}
        if (instr.definicao or {}).get("kind") == "likert_sum":
            p = pontuar_likert(instr.definicao, r.respostas or {})
            if p["tipo"] == "unico" and p["completo"]:
                meta.update(escore=p["escore"], faixa=p["faixa_rotulo"], severidade=p["severidade"])
            elif p["tipo"] == "subescalas" and p["completo"]:
                meta["subescores"] = [
                    {"rotulo": s["rotulo"], "escore": s["escore"],
                     "faixa": s["faixa_rotulo"], "severidade": s["severidade"]}
                    for s in p["subescores"]
                ]
        eventos.append(EventoTimeline(
            data=r.criado_em, tipo_evento="instrumento", ref_id=str(r.id),
            titulo=instr.titulo, meta=meta,
        ))

    # Documentos
    q_doc = select(DocumentoCFP).where(DocumentoCFP.tenant_id == tid, DocumentoCFP.paciente_id == pac.id)
    for d in (await session.scalars(q_doc)).all():
        eventos.append(EventoTimeline(
            data=d.criado_em, tipo_evento="documento", ref_id=str(d.id),
            titulo=d.tipo.replace("_", " ").capitalize(),
            meta={"status": d.status, "tipo": d.tipo},
        ))

    eventos.sort(key=lambda ev: ev.data, reverse=True)
    return TimelineOut(eventos=eventos)


# --------------------------------------------------------------------------
# Trajetória de escores (likert_sum)
# --------------------------------------------------------------------------

@router.get("/pacientes/{paciente_id}/trajetoria", response_model=TrajetoriaOut)
async def trajetoria(
    paciente_id: str,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> TrajetoriaOut:
    pac = await _assert_paciente(session, user, paciente_id)

    # Só aplicações FINALIZADAS entram na trajetória (registro imutável). A linha
    # do tempo mostra todas as aplicações; a tendência usa apenas as fechadas.
    q = (
        select(RespostaInstrumento, Instrumento)
        .join(Instrumento, Instrumento.id == RespostaInstrumento.instrumento_id)
        .where(
            RespostaInstrumento.tenant_id == user.tenant_id,
            RespostaInstrumento.paciente_id == pac.id,
            RespostaInstrumento.status == "finalizado",
        )
        .order_by(RespostaInstrumento.criado_em)
    )
    rows = (await session.execute(q)).all()

    # Acumula pontos por chave de série, preservando metadados da série.
    series: dict[str, SerieTrajetoria] = {}

    def serie(chave: str, titulo: str, definicao: dict, subescala: dict | None) -> SerieTrajetoria:
        if chave not in series:
            faixas = (subescala["faixas"] if subescala else definicao.get("faixas", [])) or []
            series[chave] = SerieTrajetoria(
                tipo=chave, titulo=titulo,
                escore_min=(faixas[0]["min"] if faixas else 0),
                escore_max=_escore_max(definicao, subescala),
                faixas=[FaixaDef(**f) for f in faixas],
                pontos=[],
            )
        return series[chave]

    for r, instr in rows:
        definicao = instr.definicao or {}
        if definicao.get("kind") != "likert_sum":
            continue
        p = pontuar_likert(definicao, r.respostas or {})

        if p["tipo"] == "unico":
            if not p["completo"]:
                continue
            s = serie(instr.tipo, instr.titulo, definicao, None)
            s.pontos.append(PontoSerie(
                data=r.criado_em, escore=p["escore"], faixa=p["faixa_rotulo"],
                severidade=p["severidade"], resposta_id=str(r.id),
            ))
        else:  # subescalas — uma série por subescala
            sub_defs = {s["id"]: s for s in definicao.get("subescalas", [])}
            for sub in p["subescores"]:
                if not sub["completo"]:
                    continue
                sub_def = sub_defs.get(sub["id"])
                if sub_def is None:
                    continue
                s = serie(f"{instr.tipo}:{sub['id']}", f"{instr.titulo} · {sub['rotulo']}", definicao, sub_def)
                s.pontos.append(PontoSerie(
                    data=r.criado_em, escore=sub["escore"], faixa=sub["faixa_rotulo"],
                    severidade=sub["severidade"], resposta_id=str(r.id),
                ))

    # Só devolve séries com pelo menos 1 ponto; ordena por título.
    ordenadas = sorted((s for s in series.values() if s.pontos), key=lambda s: s.titulo)
    return TrajetoriaOut(series=ordenadas)


# --------------------------------------------------------------------------
# Resumo factual
# --------------------------------------------------------------------------

@router.get("/pacientes/{paciente_id}/resumo", response_model=ResumoOut)
async def resumo(
    paciente_id: str,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> ResumoOut:
    pac = await _assert_paciente(session, user, paciente_id)
    tid = user.tenant_id

    # Contagem de sessões por status, num round-trip.
    q_status = (
        select(Sessao.status, func.count())
        .where(Sessao.tenant_id == tid, Sessao.paciente_id == pac.id)
        .group_by(Sessao.status)
    )
    por_status = {st: int(n) for st, n in (await session.execute(q_status)).all()}
    realizadas = por_status.get("realizada", 0)
    faltas = por_status.get("falta", 0)
    canceladas = por_status.get("cancelada", 0)
    agendadas = por_status.get("agendada", 0)
    total = realizadas + faltas + canceladas + agendadas

    # Primeira/última sessão (por data).
    q_minmax = select(func.min(Sessao.data), func.max(Sessao.data)).where(
        Sessao.tenant_id == tid, Sessao.paciente_id == pac.id
    )
    primeira, ultima = (await session.execute(q_minmax)).one()

    # Evoluções assinadas/rascunho (paciente via sessão).
    q_evo = (
        select(Evolucao.assinado_em)
        .join(Sessao, Sessao.id == Evolucao.sessao_id)
        .where(Evolucao.tenant_id == tid, Sessao.paciente_id == pac.id)
    )
    evo_rows = (await session.scalars(q_evo)).all()
    assinadas = sum(1 for a in evo_rows if a is not None)
    rascunho = len(evo_rows) - assinadas

    # Instrumentos aplicados (todas as respostas do paciente).
    aplicados = int((await session.scalar(
        select(func.count()).select_from(RespostaInstrumento).where(
            RespostaInstrumento.tenant_id == tid, RespostaInstrumento.paciente_id == pac.id
        )
    )) or 0)

    return ResumoOut(
        sessoes=SessoesResumo(
            realizadas=realizadas, faltas=faltas, canceladas=canceladas,
            agendadas_futuras=agendadas, total=total,
        ),
        adesao=Adesao(num=realizadas, den=realizadas + faltas),
        evolucoes=EvolucoesResumo(assinadas=assinadas, rascunho=rascunho),
        instrumentos_aplicados=aplicados,
        primeira_sessao=primeira, ultima_sessao=ultima,
    )
