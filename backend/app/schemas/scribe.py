from __future__ import annotations

from pydantic import BaseModel, Field


class ResumoIn(BaseModel):
    texto: str = Field(min_length=10, max_length=20000)


class ScribeOut(BaseModel):
    evolucao_id: str
    modo: str
    provider_transc: str | None
    provider_estrut: str
    prompt_versao: str
    latencia_ms: int
    audio_deletado: bool
    # Sinal (não-diagnóstico) de que o relato menciona risco de suicídio/autolesão —
    # sugere ao profissional registrar uma avaliação de risco formal (C-SSRS).
    risco_sinalizado: bool = False
    aviso: str = (
        "Rascunho gerado por IA. Revise e assine manualmente — a responsabilidade "
        "técnica pela conduta é do profissional (Manual CFP 2025)."
    )
