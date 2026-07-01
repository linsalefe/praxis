"""Busca top-k em acervo_chunks por similaridade cosseno (pgvector)."""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings


@dataclass
class Hit:
    chunk_id: str
    documento_id: str
    slug: str
    titulo: str
    autor: str
    editora: str | None
    is_terceiro: bool
    capitulo: str | None
    pagina_inicio: int | None
    pagina_fim: int | None
    texto: str
    similaridade: float  # 0..1 (1 = idêntico)


async def buscar(session: AsyncSession, embedding: list[float], top_k: int | None = None) -> list[Hit]:
    s = get_settings()
    k = top_k or s.rag_topk
    q = text(
        """
        SELECT c.id, c.documento_id, c.capitulo, c.pagina_inicio, c.pagina_fim,
               c.texto,
               d.slug, d.titulo, d.autor, d.editora, d.is_terceiro,
               1 - (c.embedding <=> CAST(:q AS vector)) AS sim
        FROM acervo_chunks c
        JOIN acervo_documentos d ON d.id = c.documento_id
        ORDER BY c.embedding <=> CAST(:q AS vector)
        LIMIT :k
        """
    ).bindparams(bindparam("q"), bindparam("k"))

    rows = (await session.execute(q, {"q": str(embedding), "k": k})).mappings().all()
    return [
        Hit(
            chunk_id=str(r["id"]),
            documento_id=str(r["documento_id"]),
            slug=r["slug"],
            titulo=r["titulo"],
            autor=r["autor"],
            editora=r["editora"],
            is_terceiro=bool(r["is_terceiro"]),
            capitulo=r["capitulo"],
            pagina_inicio=r["pagina_inicio"],
            pagina_fim=r["pagina_fim"],
            texto=r["texto"],
            similaridade=float(r["sim"]),
        )
        for r in rows
    ]
