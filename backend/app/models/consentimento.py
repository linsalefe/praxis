from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Consentimento(Base):
    __tablename__ = "consentimentos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    paciente_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("pacientes.id", ondelete="RESTRICT"), nullable=False, index=True)

    tipo: Mapped[str] = mapped_column(String(32), nullable=False)  # tratamento_dados | gravacao | compartilhamento
    texto_aceito: Mapped[str] = mapped_column(Text, nullable=False)
    aceito_por: Mapped[str] = mapped_column(String(160), nullable=False)  # nome de quem aceitou
    aceito_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
