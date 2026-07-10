"""Schemas do fluxo de posvenção (cuidado após morte por suicídio)."""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

VinculoPerda = Literal["proprio_paciente", "familiar", "amigo", "pessoa_rede", "outro"]
StatusPosvencao = Literal["aberto", "em_acompanhamento", "concluido"]


class PosvencaoCreate(BaseModel):
    ocorrido_em: date
    vinculo_perda: VinculoPerda
    status: StatusPosvencao = "aberto"
    # Passos do protocolo: dict passo_id -> texto. Chaves validadas no router.
    plano_posvencao: dict[str, str] = Field(default_factory=dict)
    observacoes: str | None = None


class PosvencaoUpdate(BaseModel):
    """Atualização parcial — posvenção é um processo (o status evolui)."""
    ocorrido_em: date | None = None
    vinculo_perda: VinculoPerda | None = None
    status: StatusPosvencao | None = None
    plano_posvencao: dict[str, str] | None = None
    observacoes: str | None = None


class PosvencaoOut(BaseModel):
    id: str
    paciente_id: str
    ocorrido_em: date
    vinculo_perda: str
    status: str
    plano_posvencao: dict[str, str]
    observacoes: str | None
    passos_preenchidos: int
    registrado_em: datetime
    criado_em: datetime


class PosvencaoResumo(BaseModel):
    """Item de lista — sem o plano detalhado (sensível)."""
    id: str
    paciente_id: str
    ocorrido_em: date
    vinculo_perda: str
    status: str
    passos_preenchidos: int
