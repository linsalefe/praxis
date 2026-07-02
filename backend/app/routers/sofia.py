"""Rotas da Sofia — RAG sobre o acervo, com guardrails clínicos e LGPD."""
from __future__ import annotations

import hashlib
import json
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select

from app.config import get_settings
from app.deps import SessionDep, get_current_user
from app.models.acervo import AcervoChunk, AcervoDocumento
from app.models.audit import AuditLog
from app.models.consentimento import Consentimento
from app.models.paciente import Paciente
from app.models.user import User
from app.rag.embeddings import embed_query
from app.rag.retriever import Hit, buscar
from app.rag.sofia import calcular_sem_respaldo, responder, responder_stream
from app.schemas.sofia import (
    CitacaoOut,
    DocumentoOut,
    PerguntarIn,
    PerguntarOut,
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
    try:
        pid = uuid.UUID(paciente_id)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "paciente_id inválido")
    pac = await session.get(Paciente, pid)
    if not pac or pac.tenant_id != user.tenant_id or pac.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Paciente não encontrado")
    cons = await session.scalar(
        select(Consentimento).where(
            Consentimento.tenant_id == user.tenant_id,
            Consentimento.paciente_id == pac.id,
            Consentimento.tipo == "tratamento_dados",
        )
    )
    if cons is None:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Sem consentimento LGPD 'tratamento_dados' registrado para este paciente. "
            "Registre o consentimento antes de consultar Sofia sobre este caso.",
        )
    return pac


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

    # 3) auditoria — armazena hash da pergunta, nunca o texto integral
    pergunta_hash = hashlib.sha256(body.pergunta.encode("utf-8")).hexdigest()
    session.add(AuditLog(
        tenant_id=user.tenant_id, user_id=user.id, acao="SOFIA_ASK",
        entidade="SofiaQuery", entidade_id=None,
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
    await session.commit()

    return PerguntarOut(
        resposta=resp.resposta,
        citacoes=[_to_citacao(i, h) for i, h in enumerate(hits, start=1)],
        sem_respaldo=resp.sem_respaldo,
        usou_paciente=usou_paciente,
        modelo=resp.modelo,
        disclaimer=DISCLAIMER,
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
        entidade="SofiaQuery", entidade_id=None,
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
        try:
            async for delta in responder_stream(body.pergunta, hits, sobre_paciente=usou_paciente):
                yield _sse("token", {"delta": delta})
        except Exception:  # noqa: BLE001 — falha do provedor vira evento SSE
            yield _sse("error", {"message": "Falha ao consultar a Sofia. Tente novamente."})
            return

        yield _sse("done", {
            "citacoes": citacoes,
            "sem_respaldo": sem_respaldo,
            "usou_paciente": usou_paciente,
            "modelo": modelo,
            "disclaimer": DISCLAIMER,
        })

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


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
