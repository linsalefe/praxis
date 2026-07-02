from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class SofiaConversa(Base):
    """Conversa com a Sofia — agrupa turnos de um profissional (escopo tenant/usuário)."""

    __tablename__ = "sofia_conversas"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    paciente_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("pacientes.id", ondelete="SET NULL"), nullable=True)
    titulo: Mapped[str] = mapped_column(Text, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class SofiaTurno(Base):
    """Um par pergunta/resposta dentro de uma conversa. Cada pergunta é isolada
    (a Sofia não recebe turnos anteriores); o turno serve só para reabrir/consultar."""

    __tablename__ = "sofia_turnos"
    __table_args__ = (UniqueConstraint("conversa_id", "ordem", name="uq_sofia_turno_ordem"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    conversa_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sofia_conversas.id", ondelete="CASCADE"), nullable=False, index=True)
    ordem: Mapped[int] = mapped_column(Integer, nullable=False)
    pergunta: Mapped[str] = mapped_column(Text, nullable=False)
    resposta: Mapped[str] = mapped_column(Text, nullable=False)
    citacoes: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default="[]")
    sem_respaldo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    usou_paciente: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    modelo: Mapped[str | None] = mapped_column(Text, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
