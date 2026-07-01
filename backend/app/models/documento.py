from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CHAR, Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class DocumentoCFP(Base):
    __tablename__ = "documentos_cfp"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    paciente_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("pacientes.id", ondelete="RESTRICT"), nullable=False, index=True)
    autor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)

    tipo: Mapped[str] = mapped_column(String(24), nullable=False)
    finalidade: Mapped[str] = mapped_column(Text, nullable=False)
    destinatario: Mapped[str | None] = mapped_column(Text, nullable=True)

    conteudo: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="rascunho")

    provider: Mapped[str | None] = mapped_column(String(80), nullable=True)
    prompt_versao: Mapped[str | None] = mapped_column(String(16), nullable=True)

    assinado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    hash_assinatura: Mapped[str | None] = mapped_column(CHAR(64), nullable=True)
    anexo_pdf_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("anexos_prontuario.id", ondelete="SET NULL"), nullable=True)

    # Tier de assinatura: 'simples' (hash) | 'icp_brasil' (PAdES/A1). Ver migração 011.
    assinatura_tipo: Mapped[str] = mapped_column(String(16), nullable=False, default="simples")
    cert_titular: Mapped[str | None] = mapped_column(Text, nullable=True)
    assinatura_valida: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
