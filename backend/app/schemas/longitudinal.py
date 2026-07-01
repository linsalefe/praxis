"""Schemas do acompanhamento longitudinal (read-only, factual)."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


# --- Timeline unificada -----------------------------------------------------

class EventoTimeline(BaseModel):
    data: datetime
    tipo_evento: str  # sessao | evolucao | instrumento | documento
    titulo: str
    ref_id: str
    meta: dict[str, Any] = {}


class TimelineOut(BaseModel):
    eventos: list[EventoTimeline]


# --- Trajetória de escores (likert_sum) ------------------------------------

class FaixaDef(BaseModel):
    min: int
    max: int | None
    rotulo: str
    severidade: str


class PontoSerie(BaseModel):
    data: datetime
    escore: int
    faixa: str | None
    severidade: str | None
    resposta_id: str


class SerieTrajetoria(BaseModel):
    tipo: str          # "phq9" | "dass21:depressao" | ...
    titulo: str
    escore_min: int
    escore_max: int
    faixas: list[FaixaDef]
    pontos: list[PontoSerie]


class TrajetoriaOut(BaseModel):
    series: list[SerieTrajetoria]


# --- Resumo factual ---------------------------------------------------------

class SessoesResumo(BaseModel):
    realizadas: int
    faltas: int
    canceladas: int
    agendadas_futuras: int
    total: int


class Adesao(BaseModel):
    num: int
    den: int
    criterio: str = "realizadas ÷ (realizadas + faltas)"


class EvolucoesResumo(BaseModel):
    assinadas: int
    rascunho: int


class ResumoOut(BaseModel):
    sessoes: SessoesResumo
    adesao: Adesao
    evolucoes: EvolucoesResumo
    instrumentos_aplicados: int
    primeira_sessao: datetime | None
    ultima_sessao: datetime | None
