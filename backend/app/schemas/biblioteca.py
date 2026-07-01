"""Schemas da Biblioteca viva — navegação + busca semântica read-only.

Nenhum schema aqui expõe texto integral de chunk: o índice é pura estrutura
e os hits de busca carregam apenas `trecho` já cortado pelo guardrail da Sofia
(SNIPPET_TERCEIRO / SNIPPET_PROPRIO).
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class ObraOut(BaseModel):
    id: str
    slug: str
    titulo: str
    autor: str
    editora: str | None
    ano: int | None
    is_terceiro: bool
    total_chunks: int


class IndiceItemOut(BaseModel):
    ordem: int
    capitulo: str | None
    secao_titulo: str | None            # sempre null na ingestão atual; mantido por fidelidade
    pagina_inicio: int | None
    pagina_fim: int | None


class ObraDetalheOut(BaseModel):
    obra: ObraOut
    indice: list[IndiceItemOut]


class BuscarIn(BaseModel):
    q: str = Field(min_length=3, max_length=2000)
    obra: str | None = None             # slug para restringir a busca a uma obra
    top_k: int | None = Field(default=None, ge=1, le=20)


class BuscaHitOut(BaseModel):
    slug: str
    titulo: str
    capitulo: str | None
    pagina_inicio: int | None
    pagina_fim: int | None
    trecho: str                         # já cortado por _snippet (180/320 chars)
    is_terceiro: bool
    similaridade: float
