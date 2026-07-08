from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Sessao(Base):
    __tablename__ = "sessoes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    paciente_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("pacientes.id", ondelete="RESTRICT"), nullable=False, index=True)
    # Caso ao qual a sessão pertence (opcional; consultório pode não usar caso).
    caso_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("casos.id", ondelete="SET NULL"), nullable=True, index=True)

    data: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    modalidade: Mapped[str] = mapped_column(String(16), nullable=False)  # presencial | online
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="agendada")  # agendada | realizada | cancelada | falta

    valor_centavos: Mapped[int | None] = mapped_column(Integer, nullable=True)  # valor da sessão em centavos

    sala_url: Mapped[str | None] = mapped_column(Text, nullable=True)  # sala de vídeo (só em modalidade=online)

    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
