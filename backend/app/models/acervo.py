from __future__ import annotations

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.config import get_settings
from app.db import Base

EMBED_DIM = get_settings().embed_dim


class AcervoDocumento(Base):
    __tablename__ = "acervo_documentos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    slug: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    titulo: Mapped[str] = mapped_column(Text, nullable=False)
    autor: Mapped[str] = mapped_column(Text, nullable=False)
    editora: Mapped[str | None] = mapped_column(Text, nullable=True)
    ano: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_terceiro: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    fonte_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class AcervoChunk(Base):
    __tablename__ = "acervo_chunks"
    __table_args__ = (
        UniqueConstraint("documento_id", "ordem", name="uq_chunk_doc_ordem"),
        UniqueConstraint("chunk_hash", name="uq_chunk_hash"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    documento_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("acervo_documentos.id", ondelete="CASCADE"), nullable=False, index=True)
    ordem: Mapped[int] = mapped_column(Integer, nullable=False)
    capitulo: Mapped[str | None] = mapped_column(Text, nullable=True)
    secao_titulo: Mapped[str | None] = mapped_column(Text, nullable=True)
    pagina_inicio: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pagina_fim: Mapped[int | None] = mapped_column(Integer, nullable=True)
    texto: Mapped[str] = mapped_column(Text, nullable=False)
    tokens_aprox: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chunk_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBED_DIM), nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
