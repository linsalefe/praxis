from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Caso(Base):
    """Agregador clínico de um paciente (a espinha Caso/PTS).

    Consultório: 1 caso = 1 paciente (caminho simples). Serviço: caso rico com
    PTS versionado, sessões, risco e (próximas ondas) rede/grupos pendurados.
    Sigilo por profissional via `criado_por`.
    """

    __tablename__ = "casos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    paciente_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("pacientes.id", ondelete="RESTRICT"), nullable=False, index=True)
    criado_por: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)

    titulo: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ativo")  # ativo | encerrado
    # Compartilhamento com a equipe (Onda 2.1). false = sigilo estrito por
    # profissional (padrão); true = caso visível/editável por toda a equipe clínica
    # do tenant. Alterado só pelo dono do caso/owner (ver routers/casos.py).
    compartilhado: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false", default=False)
    aberto_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    encerrado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class PtsVersao(Base):
    """Uma versão do Projeto Terapêutico Singular de um caso.

    Cada save cria uma nova versão (imutável); a "atual" é a de maior `versao`.
    `conteudo` é JSONB com as seções do PTS (compreensão, metas, ações,
    reavaliação) — narrativa clínica em claro, como as evoluções.
    """

    __tablename__ = "pts_versoes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    caso_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("casos.id", ondelete="CASCADE"), nullable=False, index=True)
    versao: Mapped[int] = mapped_column(Integer, nullable=False)
    conteudo: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    criado_por: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
