"""Schemas da assinatura digital ICP-Brasil (certificado A1 + PAdES)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CertificadoOut(BaseModel):
    """Metadados do certificado — NUNCA inclui o arquivo nem a senha."""
    titular: str
    emissor: str | None
    validade_ate: datetime
    criado_em: datetime
    expirado: bool


class AssinarICPIn(BaseModel):
    # Senha do PKCS#12, usada só em memória no ato de assinar; nunca persistida.
    senha: str = Field(min_length=1, max_length=256)


class VerificacaoAssinaturaOut(BaseModel):
    assinatura_tipo: str
    cert_titular: str | None = None
    assinado_em: datetime | None = None
    assinado: bool = False
    intacto: bool | None = None
    valido: bool | None = None
    confiavel: bool | None = None
    titular: str | None = None
    algoritmo: str | None = None
    nota: str | None = None
