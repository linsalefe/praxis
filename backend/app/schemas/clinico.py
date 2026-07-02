from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


class PacienteCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=160)
    contato: str | None = None
    nascimento: date | None = None
    documento: str | None = None
    sexo: str | None = None


class PacienteUpdate(BaseModel):
    nome: str | None = None
    contato: str | None = None
    nascimento: date | None = None
    documento: str | None = None
    sexo: str | None = None


class PacienteOut(BaseModel):
    id: str
    nome: str
    contato: str | None
    nascimento: date | None
    documento: str | None
    sexo: str | None
    criado_em: datetime
    atualizado_em: datetime


class SessaoCreate(BaseModel):
    paciente_id: str
    data: datetime
    modalidade: Literal["presencial", "online"]
    status: Literal["agendada", "realizada", "cancelada", "falta"] = "agendada"
    valor_centavos: int | None = Field(default=None, ge=0)  # ausente → puxa padrão do paciente


class SessaoUpdate(BaseModel):
    data: datetime | None = None
    modalidade: Literal["presencial", "online"] | None = None
    status: Literal["agendada", "realizada", "cancelada", "falta"] | None = None
    valor_centavos: int | None = Field(default=None, ge=0)


class SessaoOut(BaseModel):
    id: str
    paciente_id: str
    data: datetime
    modalidade: str
    status: str
    valor_centavos: int | None
    sala_url: str | None
    criado_em: datetime


class SessaoAgendaOut(BaseModel):
    """Sessão na agenda, com nome do paciente decifrado (espelha SessaoHoje)."""
    id: str
    paciente_id: str
    paciente_nome: str
    data: datetime
    modalidade: str
    status: str
    valor_centavos: int | None
    sala_url: str | None


class SalaStatusOut(BaseModel):
    """Status da sala de telessessão + gate de consentimento (CFP)."""
    sessao_id: str
    modalidade: str
    consentimento_teleatendimento: bool
    sala_url: str | None       # null enquanto não houver consentimento
    link_paciente: str | None  # mesma URL Jitsi (quem tem o link entra)


class EvolucaoCreate(BaseModel):
    sessao_id: str
    identificacao: str | None = None
    demanda_objetivos: str | None = None
    evolucao: str | None = None
    encaminhamento: str | None = None


class EvolucaoUpdate(BaseModel):
    identificacao: str | None = None
    demanda_objetivos: str | None = None
    evolucao: str | None = None
    encaminhamento: str | None = None


class EvolucaoOut(BaseModel):
    id: str
    sessao_id: str
    paciente_id: str | None = None
    autor_id: str
    identificacao: str | None
    demanda_objetivos: str | None
    evolucao: str | None
    encaminhamento: str | None
    assinado_em: datetime | None
    hash_assinatura: str | None
    criado_em: datetime
    atualizado_em: datetime


class IaLogItemOut(BaseModel):
    """Um evento real de uso de IA (derivado do audit_log)."""
    acao: str
    recurso: str
    ts: datetime | None
    entidade: str
    entidade_id: str | None


class TcleIaOut(BaseModel):
    versao: str
    texto: str


class ConsentimentoCreate(BaseModel):
    paciente_id: str
    tipo: Literal["tratamento_dados", "gravacao", "compartilhamento", "teleatendimento", "uso_ia"]
    texto_aceito: str = Field(min_length=1)
    aceito_por: str = Field(min_length=1, max_length=160)


class ConsentimentoOut(BaseModel):
    id: str
    paciente_id: str
    tipo: str
    texto_aceito: str
    aceito_por: str
    aceito_em: datetime
