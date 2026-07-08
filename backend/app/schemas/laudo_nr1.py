"""Schemas do laudo de risco psicossocial NR-1 (Onda 3.1)."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class FatorAvaliado(BaseModel):
    nivel: Literal["na", "baixo", "medio", "alto"] = "na"
    observacao: str | None = None


class LaudoNR1Create(BaseModel):
    organizacao: str
    setor: str | None = None
    responsavel: str | None = None


class LaudoNR1Update(BaseModel):
    organizacao: str | None = None
    setor: str | None = None
    responsavel: str | None = None
    analise: str | None = None
    recomendacoes: str | None = None
    # fatores: fator_id -> {nivel, observacao}. Chaves validadas no router.
    fatores: dict[str, FatorAvaliado] | None = None


class LaudoNR1Out(BaseModel):
    id: str
    organizacao: str
    setor: str | None
    data: datetime
    fatores: dict[str, FatorAvaliado]
    analise: str | None
    recomendacoes: str | None
    responsavel: str | None
    status: str
    finalizado_em: datetime | None
    criado_em: datetime


class LaudoNR1Resumo(BaseModel):
    id: str
    organizacao: str
    setor: str | None
    data: datetime
    status: str
    fatores_alto: int  # nº de fatores avaliados como risco alto
