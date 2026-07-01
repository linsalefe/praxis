from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator


class AnalisarIn(BaseModel):
    paciente_id: str | None = None
    caso_texto: str | None = Field(default=None, min_length=30, max_length=8000)

    @model_validator(mode="after")
    def um_ou_outro(self) -> "AnalisarIn":
        # Exatamente um dos dois deve ser fornecido.
        if bool(self.paciente_id) == bool(self.caso_texto):
            raise ValueError(
                "Envie exatamente um: 'paciente_id' OU 'caso_texto' "
                "(mín. 30 caracteres)."
            )
        return self


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


class EstudoSalvarIn(BaseModel):
    texto_analise: str | None = None


class EstudoOut(BaseModel):
    id: str
    tenant_id: str
    autor_id: str
    origem: str
    paciente_id: str | None
    caso_hash: str | None
    texto_analise: str
    citacoes: list[CitacaoOut]
    provider: str | None
    meta: dict[str, Any]
    criado_em: datetime
    atualizado_em: datetime
    disclaimer: str = (
        "Este material é apoio formativo. A responsabilidade técnica pela "
        "conduta clínica é do profissional (Manual CFP 2025)."
    )


class EstudoResumoOut(BaseModel):
    """Item da lista — texto truncado para preview."""
    id: str
    origem: str
    paciente_id: str | None
    preview: str
    provider: str | None
    criado_em: datetime
    atualizado_em: datetime
