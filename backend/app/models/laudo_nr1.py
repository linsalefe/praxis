from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class LaudoNR1(Base):
    """Laudo de risco psicossocial NR-1 — documento organizacional (Onda 3.1).

    Sobre uma organização/setor, não um paciente. Sigilo por profissional via
    `criado_por`. `fatores` = fator_id -> {nivel, observacao}.
    """

    __tablename__ = "laudos_nr1"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    criado_por: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)

    organizacao: Mapped[str] = mapped_column(Text, nullable=False)
    setor: Mapped[str | None] = mapped_column(Text, nullable=True)
    data: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    fatores: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    analise: Mapped[str | None] = mapped_column(Text, nullable=True)
    recomendacoes: Mapped[str | None] = mapped_column(Text, nullable=True)
    responsavel: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="rascunho")
    finalizado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
