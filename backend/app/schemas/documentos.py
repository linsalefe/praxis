from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


TipoDocumento = Literal["declaracao", "atestado", "relatorio", "laudo", "encaminhamento"]


class GerarIn(BaseModel):
    paciente_id: str
    tipo: TipoDocumento
    finalidade: str = Field(min_length=3, max_length=500)
    destinatario: str | None = None


class DocumentoBlocoTemplate(BaseModel):
    id: str
    label: str
    hint: str
    palavras_alvo: tuple[int, int]


class DocumentoTemplateOut(BaseModel):
    tipo: TipoDocumento
    titulo: str
    descricao: str
    blocos: list[DocumentoBlocoTemplate]


class DocumentoSalvarIn(BaseModel):
    conteudo: dict[str, str] | None = None
    finalidade: str | None = None
    destinatario: str | None = None


class DocumentoOut(BaseModel):
    id: str
    tenant_id: str
    paciente_id: str
    autor_id: str
    tipo: str
    finalidade: str
    destinatario: str | None
    conteudo: dict[str, Any]
    status: str
    provider: str | None
    prompt_versao: str | None
    assinado_em: datetime | None
    hash_assinatura: str | None
    anexo_pdf_id: str | None
    assinatura_tipo: str = "simples"
    cert_titular: str | None = None
    criado_em: datetime
    atualizado_em: datetime
    aviso: str = (
        "Rascunho gerado por IA. Revise e assine manualmente — a "
        "responsabilidade técnica pela conduta é do profissional (Manual CFP 2025)."
    )
