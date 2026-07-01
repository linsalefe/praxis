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


class SessaoUpdate(BaseModel):
    data: datetime | None = None
    modalidade: Literal["presencial", "online"] | None = None
    status: Literal["agendada", "realizada", "cancelada", "falta"] | None = None


class SessaoOut(BaseModel):
    id: str
    paciente_id: str
    data: datetime
    modalidade: str
    status: str
    criado_em: datetime


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
    autor_id: str
    identificacao: str | None
    demanda_objetivos: str | None
    evolucao: str | None
    encaminhamento: str | None
    assinado_em: datetime | None
    hash_assinatura: str | None
    criado_em: datetime
    atualizado_em: datetime


class ConsentimentoCreate(BaseModel):
    paciente_id: str
    tipo: Literal["tratamento_dados", "gravacao", "compartilhamento"]
    texto_aceito: str = Field(min_length=1)
    aceito_por: str = Field(min_length=1, max_length=160)


class ConsentimentoOut(BaseModel):
    id: str
    paciente_id: str
    tipo: str
    texto_aceito: str
    aceito_por: str
    aceito_em: datetime
