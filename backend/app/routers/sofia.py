"""Rotas da Sofia — RAG sobre o acervo, com guardrails clínicos e LGPD."""
from __future__ import annotations

import hashlib
import json
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select

from app.authz import carregar_paciente
from app.config import get_settings
from app.conformidade.ia_cfp import exigir_uso_ia
from app.db import SessionLocal
from app.deps import SessionDep, get_current_user
from app.models.acervo import AcervoChunk, AcervoDocumento
from app.models.audit import AuditLog
from app.models.consentimento import Consentimento
from app.models.paciente import Paciente
from app.models.sofia import SofiaConversa, SofiaTurno
from app.models.user import User
from app.rag.embeddings import embed_query
from app.rag.retriever import Hit, buscar
from app.rag.sofia import calcular_sem_respaldo, responder, responder_stream
from app.schemas.sofia import (
    CitacaoOut,
    ConversaDetalheOut,
    ConversaResumoOut,
    DocumentoOut,
    PerguntarIn,
    PerguntarOut,
    TurnoOut,
)

router = APIRouter(prefix="/sofia", tags=["sofia"])

DISCLAIMER = (
    "Esta resposta é apoio ao raciocínio clínico; a responsabilidade técnica "
    "pela conduta é do profissional (Manual CFP 2025)."
)
SNIPPET_TERCEIRO = 180   # chars — chunks de terceiros são truncados no snippet
SNIPPET_PROPRIO = 320


def _snippet(hit: Hit) -> str:
    limit = SNIPPET_TERCEIRO if hit.is_terceiro else SNIPPET_PROPRIO
    t = hit.texto.strip().replace("\n", " ")
    return (t[:limit] + "…") if len(t) > limit else t


def _to_citacao(i: int, h: Hit) -> CitacaoOut:
    return CitacaoOut(
        n=i,
        documento_id=h.documento_id,
        slug=h.slug,
        titulo=h.titulo,
        autor=h.autor,
        editora=h.editora,
        is_terceiro=h.is_terceiro,
        capitulo=h.capitulo,
        pagina_inicio=h.pagina_inicio,
        pagina_fim=h.pagina_fim,
        snippet=_snippet(h),
        similaridade=round(h.similaridade, 3),
    )


async def _validar_paciente_e_consentimento(
    session, user: User, paciente_id: str
) -> Paciente:
    # Escopo por profissional (P1): valida tenant + dono + não-deletado.
    pac = await carregar_paciente(session, user, paciente_id)
    cons = await session.scalar(
        select(Consentimento).where(
            Consentimento.tenant_id == user.tenant_id,
            Consentimento.paciente_id == pac.id,
            Consentimento.tipo == "tratamento_dados",
            Consentimento.revogado_em.is_(None),
        )
    )
    if cons is None:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Sem consentimento LGPD 'tratamento_dados' registrado para este paciente. "
            "Registre o consentimento antes de consultar Sofia sobre este caso.",
        )
    await exigir_uso_ia(session, user.tenant_id, pac.id)
    return pac


# --- Histórico de conversas ------------------------------------------------
# Persistência do par pergunta/resposta por usuário/tenant. Cada turno é
# independente (a Sofia não recebe turnos anteriores); serve só para reabrir.

def _titulo_de(pergunta: str) -> str:
    t = " ".join(pergunta.strip().split())
    return (t[:80] + "…") if len(t) > 80 else t


async def _carregar_conversa(session, user: User, conversa_id: str) -> SofiaConversa:
    """Carrega uma conversa garantindo que pertence ao usuário/tenant (404 senão)."""
    try:
        cid = uuid.UUID(conversa_id)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "conversa_id inválido")
    conv = await session.get(SofiaConversa, cid)
    if conv is None or conv.tenant_id != user.tenant_id or conv.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversa não encontrada")
    return conv


async def _resolver_conversa(
    session, user: User, conversa_id: str | None, paciente_id: str | None, pergunta: str
) -> SofiaConversa:
    """Retorna a conversa existente (validando dono) ou cria uma nova. Não commita."""
    if conversa_id:
        return await _carregar_conversa(session, user, conversa_id)
    conv = SofiaConversa(
        tenant_id=user.tenant_id,
        user_id=user.id,
        paciente_id=uuid.UUID(paciente_id) if paciente_id else None,
        titulo=_titulo_de(pergunta),
    )
    session.add(conv)
    await session.flush()  # garante conv.id
    return conv


async def _gravar_turno(
    session, conv: SofiaConversa, *, pergunta: str, resposta: str,
    citacoes: list[dict], sem_respaldo: bool, usou_paciente: bool, modelo: str | None,
) -> None:
    ordem = await session.scalar(
        select(func.coalesce(func.max(SofiaTurno.ordem), 0)).where(
            SofiaTurno.conversa_id == conv.id
        )
    )
    session.add(SofiaTurno(
        conversa_id=conv.id, ordem=int(ordem or 0) + 1,
        pergunta=pergunta, resposta=resposta, citacoes=citacoes,
        sem_respaldo=sem_respaldo, usou_paciente=usou_paciente, modelo=modelo,
    ))
    conv.atualizado_em = func.now()  # sobe a conversa no topo do histórico


@router.post("/perguntar", response_model=PerguntarOut)
async def perguntar(
    body: PerguntarIn,
    request: Request,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> PerguntarOut:
    usou_paciente = False
    if body.paciente_id:
        # Validação e consentimento LGPD. Sofia NÃO recebe dados do paciente
        # (política atual): esta validação só autoriza o LOG da consulta.
        await _validar_paciente_e_consentimento(session, user, body.paciente_id)
        usou_paciente = True

    # 1) embed da pergunta + retrieve
    q_vec = await embed_query(body.pergunta)
    hits = await buscar(session, q_vec, top_k=body.top_k)

    # 2) LLM (com aviso de que é sobre paciente, mas sem PII)
    resp = await responder(body.pergunta, hits, sobre_paciente=usou_paciente)
    citacoes = [_to_citacao(i, h) for i, h in enumerate(hits, start=1)]

    # 3) histórico — grava o turno (pergunta/resposta integrais) na conversa
    conv = await _resolver_conversa(session, user, body.conversa_id, body.paciente_id, body.pergunta)
    await _gravar_turno(
        session, conv, pergunta=body.pergunta, resposta=resp.resposta,
        citacoes=[c.model_dump() for c in citacoes], sem_respaldo=resp.sem_respaldo,
        usou_paciente=usou_paciente, modelo=resp.modelo,
    )

    # 4) auditoria — armazena hash da pergunta, nunca o texto integral
    pergunta_hash = hashlib.sha256(body.pergunta.encode("utf-8")).hexdigest()
    session.add(AuditLog(
        tenant_id=user.tenant_id, user_id=user.id, acao="SOFIA_ASK",
        entidade="SofiaConversa", entidade_id=str(conv.id),
        ip=request.client.host if request.client else None,
        meta={
            "pergunta_hash": pergunta_hash,
            "pergunta_len": len(body.pergunta),
            "paciente_id": body.paciente_id,
            "chunk_ids": [h.chunk_id for h in hits],
            "sem_respaldo": resp.sem_respaldo,
            "modelo": resp.modelo,
        },
    ))
    conversa_id = str(conv.id)
    await session.commit()

    return PerguntarOut(
        resposta=resp.resposta,
        citacoes=citacoes,
        sem_respaldo=resp.sem_respaldo,
        usou_paciente=usou_paciente,
        modelo=resp.modelo,
        disclaimer=DISCLAIMER,
        conversa_id=conversa_id,
    )


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/perguntar/stream")
async def perguntar_stream(
    body: PerguntarIn,
    request: Request,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> StreamingResponse:
    """Igual a /perguntar, porém em streaming (SSE): emite `token` por delta e um
    `done` final com citações/disclaimer/modelo. O endpoint /perguntar segue
    disponível como fallback. Guardrails e citações são idênticos."""
    # Validação/consentimento e retrieval acontecem ANTES de abrir o stream, para
    # que erros retornem status HTTP normal (e não no meio do corpo já iniciado).
    usou_paciente = False
    if body.paciente_id:
        await _validar_paciente_e_consentimento(session, user, body.paciente_id)
        usou_paciente = True

    # Valida a conversa (se veio) ANTES de abrir o stream, para devolver 404 com
    # status HTTP normal (e não no meio do corpo já iniciado). A gravação do turno
    # acontece no fim do gerador, numa sessão própria.
    conv_id_valida: str | None = None
    if body.conversa_id:
        conv = await _carregar_conversa(session, user, body.conversa_id)
        conv_id_valida = str(conv.id)

    q_vec = await embed_query(body.pergunta)
    hits = await buscar(session, q_vec, top_k=body.top_k)
    citacoes = [_to_citacao(i, h).model_dump() for i, h in enumerate(hits, start=1)]
    sem_respaldo = calcular_sem_respaldo(hits)
    modelo = get_settings().llm_model

    # Auditoria ANTES de abrir o stream — o registro não depende do texto gerado
    # (igual a /perguntar: guarda hash da pergunta, chunk_ids, modelo). Assim o
    # commit não corre dentro do gerador, evitando risco com o ciclo da sessão.
    session.add(AuditLog(
        tenant_id=user.tenant_id, user_id=user.id, acao="SOFIA_ASK",
        entidade="SofiaConversa", entidade_id=conv_id_valida,
        ip=request.client.host if request.client else None,
        meta={
            "pergunta_hash": hashlib.sha256(body.pergunta.encode("utf-8")).hexdigest(),
            "pergunta_len": len(body.pergunta),
            "paciente_id": body.paciente_id,
            "chunk_ids": [h.chunk_id for h in hits],
            "sem_respaldo": sem_respaldo,
            "modelo": modelo,
            "stream": True,
        },
    ))
    await session.commit()

    async def gen():
        acc = ""
        try:
            async for delta in responder_stream(body.pergunta, hits, sobre_paciente=usou_paciente):
                acc += delta
                yield _sse("token", {"delta": delta})
        except Exception:  # noqa: BLE001 — falha do provedor vira evento SSE
            yield _sse("error", {"message": "Falha ao consultar a Sofia. Tente novamente."})
            return

        # Grava o turno numa sessão fresca — fora do ciclo da sessão do request.
        # Se a gravação falhar, a resposta ao usuário não é afetada.
        conversa_id = conv_id_valida
        try:
            async with SessionLocal() as s2:
                conv2 = await _resolver_conversa(
                    s2, user, conv_id_valida, body.paciente_id, body.pergunta
                )
                await _gravar_turno(
                    s2, conv2, pergunta=body.pergunta, resposta=acc, citacoes=citacoes,
                    sem_respaldo=sem_respaldo, usou_paciente=usou_paciente, modelo=modelo,
                )
                await s2.commit()
                conversa_id = str(conv2.id)
        except Exception:  # noqa: BLE001 — persistência é best-effort no stream
            pass

        yield _sse("done", {
            "citacoes": citacoes,
            "sem_respaldo": sem_respaldo,
            "usou_paciente": usou_paciente,
            "modelo": modelo,
            "disclaimer": DISCLAIMER,
            "conversa_id": conversa_id,
        })

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/conversas", response_model=list[ConversaResumoOut])
async def listar_conversas(
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> list[ConversaResumoOut]:
    rows = (
        await session.execute(
            select(
                SofiaConversa.id,
                SofiaConversa.titulo,
                SofiaConversa.paciente_id,
                SofiaConversa.criado_em,
                SofiaConversa.atualizado_em,
                func.count(SofiaTurno.id).label("total_turnos"),
            )
            .join(SofiaTurno, SofiaTurno.conversa_id == SofiaConversa.id, isouter=True)
            .where(
                SofiaConversa.tenant_id == user.tenant_id,
                SofiaConversa.user_id == user.id,
            )
            .group_by(SofiaConversa.id)
            .order_by(SofiaConversa.atualizado_em.desc())
        )
    ).all()
    return [
        ConversaResumoOut(
            id=str(r.id), titulo=r.titulo,
            paciente_id=str(r.paciente_id) if r.paciente_id else None,
            total_turnos=int(r.total_turnos or 0),
            criado_em=r.criado_em.isoformat(),
            atualizado_em=r.atualizado_em.isoformat(),
        )
        for r in rows
    ]


@router.get("/conversas/{conversa_id}", response_model=ConversaDetalheOut)
async def obter_conversa(
    conversa_id: str,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> ConversaDetalheOut:
    conv = await _carregar_conversa(session, user, conversa_id)
    turnos = (
        await session.execute(
            select(SofiaTurno)
            .where(SofiaTurno.conversa_id == conv.id)
            .order_by(SofiaTurno.ordem)
        )
    ).scalars().all()
    return ConversaDetalheOut(
        id=str(conv.id), titulo=conv.titulo,
        paciente_id=str(conv.paciente_id) if conv.paciente_id else None,
        criado_em=conv.criado_em.isoformat(),
        turnos=[
            TurnoOut(
                pergunta=t.pergunta, resposta=t.resposta, citacoes=t.citacoes,
                sem_respaldo=t.sem_respaldo, usou_paciente=t.usou_paciente,
                modelo=t.modelo, disclaimer=DISCLAIMER, criado_em=t.criado_em.isoformat(),
            )
            for t in turnos
        ],
    )


@router.delete("/conversas/{conversa_id}", status_code=status.HTTP_204_NO_CONTENT)
async def excluir_conversa(
    conversa_id: str,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> Response:
    conv = await _carregar_conversa(session, user, conversa_id)
    await session.delete(conv)          # turnos vão por CASCADE
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/acervo", response_model=list[DocumentoOut])
async def listar_acervo(
    session: SessionDep,
    _user: Annotated[User, Depends(get_current_user)],
) -> list[DocumentoOut]:
    q = (
        select(
            AcervoDocumento.id,
            AcervoDocumento.slug,
            AcervoDocumento.titulo,
            AcervoDocumento.autor,
            AcervoDocumento.editora,
            AcervoDocumento.ano,
            AcervoDocumento.is_terceiro,
            func.count(AcervoChunk.id).label("total_chunks"),
        )
        .join(AcervoChunk, AcervoChunk.documento_id == AcervoDocumento.id, isouter=True)
        .group_by(AcervoDocumento.id)
        .order_by(AcervoDocumento.titulo)
    )
    rows = (await session.execute(q)).all()
    return [
        DocumentoOut(
            id=str(r.id), slug=r.slug, titulo=r.titulo, autor=r.autor,
            editora=r.editora, ano=r.ano, is_terceiro=r.is_terceiro,
            total_chunks=int(r.total_chunks or 0),
        )
        for r in rows
    ]
