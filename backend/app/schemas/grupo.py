"""Schemas de encontros de grupo/oficina/assembleia (Onda 2.2)."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ParticipanteIn(BaseModel):
    paciente_id: str | None = None
    nome_livre: str | None = None
    presente: bool = True


class ParticipanteOut(BaseModel):
    id: str
    paciente_id: str | None
    nome: str            # nome do paciente (decifrado) ou nome livre
    e_paciente: bool
    presente: bool


class EncontroCreate(BaseModel):
    tipo: Literal["grupo", "oficina", "assembleia"]
    titulo: str
    data: datetime
    local: str | None = None
    tema: str | None = None
    registro: str | None = None
    participantes: list[ParticipanteIn] = []


class EncontroUpdate(BaseModel):
    tipo: Literal["grupo", "oficina", "assembleia"] | None = None
    titulo: str | None = None
    data: datetime | None = None
    local: str | None = None
    tema: str | None = None
    registro: str | None = None


class EncontroResumo(BaseModel):
    id: str
    tipo: str
    titulo: str
    data: datetime
    local: str | None
    total_participantes: int
    presentes: int


class EncontroOut(BaseModel):
    id: str
    tipo: str
    titulo: str
    data: datetime
    local: str | None
    tema: str | None
    registro: str | None
    criado_em: datetime
    participantes: list[ParticipanteOut]
