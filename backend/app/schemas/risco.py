"""Schemas do módulo de risco (rastreio C-SSRS + Plano de Segurança)."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class CssrsRespostas(BaseModel):
    """Respostas do rastreio C-SSRS. Itens sim/não + quando do comportamento."""
    q1: bool = False
    q2: bool = False
    q3: bool = False
    q4: bool = False
    q5: bool = False
    q6: bool = False
    comportamento_quando: Literal["nao", "vida", "recente"] = "nao"


class AvaliacaoRiscoCreate(BaseModel):
    cssrs: CssrsRespostas
    # Plano de Segurança: dict passo_id -> texto. Chaves validadas no router.
    plano_seguranca: dict[str, str] = Field(default_factory=dict)
    observacoes: str | None = None
    avaliado_em: datetime | None = None


class AvaliacaoRiscoOut(BaseModel):
    id: str
    paciente_id: str
    avaliado_em: datetime
    nivel_risco: str
    gatilhos: list[str]
    recomendacao: str
    cssrs: dict[str, Any]
    plano_seguranca: dict[str, str]
    observacoes: str | None
    criado_em: datetime


class AvaliacaoRiscoResumo(BaseModel):
    """Item de lista/flag — sem o Plano de Segurança (que é sensível/detalhado)."""
    id: str
    paciente_id: str
    avaliado_em: datetime
    nivel_risco: str
    gatilhos: list[str]


class RiscoAtualOut(BaseModel):
    """Bandeira de risco no prontuário: a avaliação mais recente, se houver."""
    tem_avaliacao: bool
    nivel_risco: str | None = None
    avaliado_em: datetime | None = None
    avaliacao_id: str | None = None
