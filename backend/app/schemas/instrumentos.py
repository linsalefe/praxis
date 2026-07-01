from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class InstrumentoOut(BaseModel):
    id: str
    tipo: str
    versao: str
    titulo: str
    descricao: str | None
    fonte: str | None
    definicao: dict[str, Any] | None = None  # incluído apenas em GET /instrumentos/{tipo}


class IniciarIn(BaseModel):
    # Validado contra o catálogo (404 se o tipo não existir) — assim novas
    # escalas do catálogo ficam disponíveis sem alterar este schema.
    tipo: str = Field(min_length=1, max_length=32)


class RespostaSalvarIn(BaseModel):
    respostas: dict[str, Any] | None = None
    saida_texto: str | None = None


class SubescoreOut(BaseModel):
    id: str
    rotulo: str
    escore: int
    itens_respondidos: int
    total_itens: int
    completo: bool
    faixa_rotulo: str | None = None
    severidade: str | None = None


class PontuacaoOut(BaseModel):
    """Escore determinístico de escalas `likert_sum` (factual, calculado no backend)."""
    tipo: str  # "unico" | "subescalas"
    escore: int | None = None
    escore_bruto: int | None = None
    transformado: int | None = None
    faixa_rotulo: str | None = None
    severidade: str | None = None
    itens_respondidos: int
    total_itens: int
    completo: bool
    subescores: list[SubescoreOut] = []


class RespostaOut(BaseModel):
    id: str
    paciente_id: str
    instrumento_tipo: str
    instrumento_versao: str
    status: str
    respostas: dict[str, Any]
    saida_texto: str | None
    saida_gerada_em: datetime | None
    saida_provider: str | None
    finalizado_em: datetime | None
    anexo_id: str | None = None
    pontuacao: PontuacaoOut | None = None  # preenchido apenas p/ instrumentos likert_sum
    criado_em: datetime
    atualizado_em: datetime


class AnexoOut(BaseModel):
    id: str
    paciente_id: str
    origem_tipo: str
    origem_id: str | None
    titulo: str
    mimetype: str
    bytes: int
    sha256: str
    criado_em: datetime


class GerarSaidaOut(BaseModel):
    resposta_id: str
    saida_texto: str
    provider: str
    aviso: str = Field(
        default=(
            "Rascunho gerado por IA. Revise e finalize manualmente — a "
            "responsabilidade técnica pela conduta é do profissional (Manual CFP 2025)."
        )
    )
