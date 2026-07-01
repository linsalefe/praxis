from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, LargeBinary, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class EvolucaoGeracao(Base):
    __tablename__ = "evolucao_geracao"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    evolucao_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("evolucoes.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    modo: Mapped[str] = mapped_column(String(16), nullable=False)  # audio | resumo

    entrada_cifrada: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    entrada_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    entrada_purgada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    audio_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    audio_mimetype: Mapped[str | None] = mapped_column(String(64), nullable=True)
    audio_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    audio_deletado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    provider_transc: Mapped[str | None] = mapped_column(String(80), nullable=True)
    provider_estrut: Mapped[str | None] = mapped_column(String(80), nullable=True)
    prompt_versao: Mapped[str | None] = mapped_column(String(16), nullable=True)
    latencia_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    criado_por: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
