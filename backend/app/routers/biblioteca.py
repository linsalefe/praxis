"""Biblioteca viva — navegação e busca semântica sobre o acervo (read-only).

Reusa a busca vetorial da Sofia (embed_query + retriever.buscar) e o guardrail
de copyright (_snippet / SNIPPET_TERCEIRO / SNIPPET_PROPRIO). Não gera texto,
não toca a ingestão nem a Sofia, e nenhum endpoint devolve texto integral:
o índice é pura estrutura e os hits carregam apenas o trecho já cortado.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select

from app.deps import SessionDep, get_current_user
from app.models.acervo import AcervoChunk, AcervoDocumento
from app.models.user import User
from app.rag.embeddings import embed_query
from app.rag.retriever import buscar
from app.routers.sofia import _snippet  # guardrail único (SNIPPET_TERCEIRO/PROPRIO)
from app.schemas.biblioteca import (
    BuscaHitOut,
    BuscarIn,
    IndiceItemOut,
    ObraDetalheOut,
    ObraOut,
)

router = APIRouter(prefix="/biblioteca", tags=["biblioteca"])


def _obra_out(r) -> ObraOut:
    return ObraOut(
        id=str(r.id), slug=r.slug, titulo=r.titulo, autor=r.autor,
        editora=r.editora, ano=r.ano, is_terceiro=r.is_terceiro,
        total_chunks=int(r.total_chunks or 0),
    )


@router.get("", response_model=list[ObraOut])
async def listar_obras(
    session: SessionDep,
    _user: Annotated[User, Depends(get_current_user)],
) -> list[ObraOut]:
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
    return [_obra_out(r) for r in rows]


@router.get("/{slug}", response_model=ObraDetalheOut)
async def obter_obra(
    slug: str,
    session: SessionDep,
    _user: Annotated[User, Depends(get_current_user)],
) -> ObraDetalheOut:
    doc = await session.scalar(
        select(AcervoDocumento).where(AcervoDocumento.slug == slug)
    )
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Obra não encontrada")

    total = await session.scalar(
        select(func.count(AcervoChunk.id)).where(AcervoChunk.documento_id == doc.id)
    )

    # Índice = pura estrutura (capítulo/seção/páginas), ordenado por `ordem`.
    # Sem texto de chunk — vale igual para próprio e terceiro.
    rows = (
        await session.execute(
            select(
                AcervoChunk.ordem,
                AcervoChunk.capitulo,
                AcervoChunk.secao_titulo,
                AcervoChunk.pagina_inicio,
                AcervoChunk.pagina_fim,
            )
            .where(AcervoChunk.documento_id == doc.id)
            .order_by(AcervoChunk.ordem)
        )
    ).all()

    obra = ObraOut(
        id=str(doc.id), slug=doc.slug, titulo=doc.titulo, autor=doc.autor,
        editora=doc.editora, ano=doc.ano, is_terceiro=doc.is_terceiro,
        total_chunks=int(total or 0),
    )
    indice = [
        IndiceItemOut(
            ordem=r.ordem, capitulo=r.capitulo, secao_titulo=r.secao_titulo,
            pagina_inicio=r.pagina_inicio, pagina_fim=r.pagina_fim,
        )
        for r in rows
    ]
    return ObraDetalheOut(obra=obra, indice=indice)


@router.post("/buscar", response_model=list[BuscaHitOut])
async def buscar_semantico(
    body: BuscarIn,
    session: SessionDep,
    _user: Annotated[User, Depends(get_current_user)],
) -> list[BuscaHitOut]:
    # Reuso direto do caminho da Sofia: mesmo embedding, mesma query vetorial.
    q_vec = await embed_query(body.q)
    hits = await buscar(session, q_vec, top_k=body.top_k, slug=body.obra)
    return [
        BuscaHitOut(
            slug=h.slug,
            titulo=h.titulo,
            capitulo=h.capitulo,
            pagina_inicio=h.pagina_inicio,
            pagina_fim=h.pagina_fim,
            trecho=_snippet(h),            # 180 (terceiro) / 320 (próprio), sempre cortado
            is_terceiro=h.is_terceiro,
            similaridade=round(h.similaridade, 3),
        )
        for h in hits
    ]
