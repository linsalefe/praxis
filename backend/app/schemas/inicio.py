"""Schemas do cockpit clínico "Hoje" (agregação read-only de pendências)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class SessaoHoje(BaseModel):
    sessao_id: str
    paciente_id: str
    paciente_nome: str
    data: datetime
    modalidade: str
    status: str


class EvolucaoRascunho(BaseModel):
    evolucao_id: str
    sessao_id: str
    paciente_id: str
    paciente_nome: str
    criado_em: datetime


class DocumentoRascunho(BaseModel):
    documento_id: str
    paciente_id: str
    paciente_nome: str
    tipo: str
    finalidade: str
    criado_em: datetime


class InstrumentoPendente(BaseModel):
    resposta_id: str
    paciente_id: str
    paciente_nome: str
    instrumento_titulo: str
    criado_em: datetime


class Contadores(BaseModel):
    sessoes_hoje: int
    evolucoes_rascunho: int
    documentos_rascunho: int
    instrumentos_pendentes: int


class PendenciasOut(BaseModel):
    sessoes_hoje: list[SessaoHoje]
    evolucoes_rascunho: list[EvolucaoRascunho]
    documentos_rascunho: list[DocumentoRascunho]
    instrumentos_pendentes: list[InstrumentoPendente]
    contadores: Contadores
