from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class PrepararIn(BaseModel):
    paciente_id: str
    sessao_id: str | None = None


class CitacaoOut(BaseModel):
    n: int
    documento_id: str
    slug: str
    titulo: str
    autor: str
    is_terceiro: bool
    capitulo: str | None
    pagina_inicio: int | None
    pagina_fim: int | None
    snippet: str
    similaridade: float


class RoteiroSalvarIn(BaseModel):
    sessao_id: str | None = None
    texto: str | None = None


class RoteiroOut(BaseModel):
    id: str
    paciente_id: str
    sessao_id: str | None
    autor_id: str
    texto: str
    citacoes: list[CitacaoOut]
    provider: str | None
    meta: dict[str, Any]
    criado_em: datetime
    atualizado_em: datetime
    disclaimer: str = (
        "Este roteiro é apoio ao raciocínio clínico; a responsabilidade "
        "técnica pela conduta é do profissional (Manual CFP 2025)."
    )
