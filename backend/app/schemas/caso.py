"""Schemas de Caso e PTS (espinha Caso/PTS, Onda 1.2)."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class CasoCreate(BaseModel):
    titulo: str | None = None


class CasoUpdate(BaseModel):
    titulo: str | None = None
    status: str | None = None  # 'ativo' | 'encerrado' (validado no router)


class PtsVersaoOut(BaseModel):
    id: str
    caso_id: str
    versao: int
    conteudo: dict[str, str]
    criado_por: str
    criado_em: datetime


class CasoOut(BaseModel):
    id: str
    paciente_id: str
    titulo: str | None
    status: str
    aberto_em: datetime
    encerrado_em: datetime | None
    criado_em: datetime
    pts_atual: PtsVersaoOut | None = None


class CasoResumo(BaseModel):
    id: str
    paciente_id: str
    titulo: str | None
    status: str
    aberto_em: datetime
    pts_versao_atual: int | None = None


class PtsSalvar(BaseModel):
    # Conteúdo das seções do PTS: secao_id -> texto. Chaves validadas no router.
    conteudo: dict[str, str] = Field(default_factory=dict)


# --- Rede de apoio (genograma/ecomapa) -------------------------------------

class MembroRedeCreate(BaseModel):
    nome: str
    papel: str | None = None
    tipo_vinculo: Literal["familiar", "comunitario", "servico", "outro"] = "outro"
    forca_vinculo: Literal["forte", "fragil", "conflito"] = "forte"
    observacoes: str | None = None


class MembroRedeUpdate(BaseModel):
    nome: str | None = None
    papel: str | None = None
    tipo_vinculo: Literal["familiar", "comunitario", "servico", "outro"] | None = None
    forca_vinculo: Literal["forte", "fragil", "conflito"] | None = None
    observacoes: str | None = None


class MembroRedeOut(BaseModel):
    id: str
    caso_id: str
    nome: str
    papel: str | None
    tipo_vinculo: str
    forca_vinculo: str
    observacoes: str | None
