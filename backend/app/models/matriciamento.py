from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Matriciamento(Base):
    """Registro de apoio matricial ligado a um caso (Onda 2.4).

    Herda o sigilo por profissional do caso (via _carregar_caso). Narrativa em
    claro, como as evoluções.
    """

    __tablename__ = "matriciamentos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    caso_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("casos.id", ondelete="CASCADE"), nullable=False, index=True)
    criado_por: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)

    data: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    equipe_referencia: Mapped[str | None] = mapped_column(Text, nullable=True)
    demanda: Mapped[str | None] = mapped_column(Text, nullable=True)
    discussao: Mapped[str | None] = mapped_column(Text, nullable=True)
    combinados: Mapped[str | None] = mapped_column(Text, nullable=True)

    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
