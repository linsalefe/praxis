from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, EmailStr, Field


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
    abordagem: str | None
    papel: str
    totp_ativado: bool
    tenant_id: str
