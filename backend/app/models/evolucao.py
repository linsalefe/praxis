from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Evolucao(Base):
    """Estrutura CFP: identificação, avaliação de demanda/objetivos, evolução, encaminhamento/encerramento."""

    __tablename__ = "evolucoes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    sessao_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sessoes.id", ondelete="RESTRICT"), nullable=False, index=True)
    autor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)

    # Blocos CFP.
    identificacao: Mapped[str | None] = mapped_column(Text, nullable=True)
    demanda_objetivos: Mapped[str | None] = mapped_column(Text, nullable=True)
    evolucao: Mapped[str | None] = mapped_column(Text, nullable=True)
    encaminhamento: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Assinatura eletrônica (rascunho quando NULL).
    assinado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    hash_assinatura: Mapped[str | None] = mapped_column(String(64), nullable=True)  # sha256 hex

    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
