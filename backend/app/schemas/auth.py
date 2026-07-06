from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

# CRP no formato região/inscrição, ex.: "06/123456". Região 01–24; inscrição de
# 3 a 6 dígitos (aceita sufixo de categoria, ex.: "/6" após barra final).
_CRP_RE = re.compile(r"^\d{2}/\d{3,6}(?:/\d)?$")


ABORDAGENS = Literal[
    "dialogo_aberto",
    "ouvir_vozes",
    "gam",
    "ptmf",
    "wrap",
    "reducao_danos",
    "outros",
]


class RegisterIn(BaseModel):
    nome: str = Field(min_length=2, max_length=160)
    email: EmailStr
    senha: str = Field(min_length=8, max_length=128)
    crp: str | None = None
    abordagem: ABORDAGENS | None = None
    tenant_tipo: Literal["solo", "clinica"] = "solo"
    tenant_nome: str = Field(min_length=2, max_length=160)

    @field_validator("crp")
    @classmethod
    def _valida_crp(cls, v: str | None) -> str | None:
        if v is None:
            return None
        # Normaliza: remove prefixo "CRP" e espaços; unifica separadores.
        limpo = re.sub(r"(?i)\bcrp\b", "", v).strip()
        limpo = re.sub(r"\s+", "", limpo)
        if not limpo:
            return None
        if not _CRP_RE.match(limpo):
            raise ValueError("CRP inválido. Use o formato região/inscrição, ex.: 06/123456.")
        return limpo


class LoginIn(BaseModel):
    email: EmailStr
    senha: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    mfa_required: bool = False
    scope: str = "session"


class TotpSetupOut(BaseModel):
    otpauth_url: str
    qrcode_data_uri: str


class TotpVerifyIn(BaseModel):
    codigo: str = Field(min_length=6, max_length=8)


class TotpLoginIn(BaseModel):
    codigo: str = Field(min_length=6, max_length=8)


class MeOut(BaseModel):
    id: str
    nome: str
    email: str
    crp: str | None
    crp_verificado: bool = False
    abordagem: str | None
    papel: str
    totp_ativado: bool
    tenant_id: str
    nome_exibicao: str | None = None
    registro_profissional: str | None = None
    contato_timbre: str | None = None


class PerfilUpdateIn(BaseModel):
    """Campos editáveis do perfil (timbre dos PDFs). Todos opcionais; string
    vazia limpa o campo (volta ao fallback nome/crp)."""
    nome_exibicao: str | None = Field(default=None, max_length=160)
    registro_profissional: str | None = Field(default=None, max_length=64)
    contato_timbre: str | None = Field(default=None, max_length=255)
