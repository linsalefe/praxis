from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, LargeBinary, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class AvaliacaoRisco(Base):
    """Uma avaliação de risco de suicídio/autolesão de um paciente.

    Registro de apoio à decisão clínica (rastreio C-SSRS + Plano de Segurança).
    `nivel_risco` é derivado no servidor a partir de `cssrs` (fonte única:
    app/risco/scoring.py) e nunca confiado no cliente.
    """

    __tablename__ = "avaliacoes_risco"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    paciente_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("pacientes.id", ondelete="RESTRICT"), nullable=False, index=True)
    criado_por: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)

    avaliado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Respostas do rastreio C-SSRS (não cifrado — conteúdo clínico sem PII de terceiros).
    cssrs: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # Retrato factual do nível no momento da avaliação (derivado no servidor).
    nivel_risco: Mapped[str] = mapped_column(String(16), nullable=False)

    # Plano de Segurança (Stanley-Brown) e observações contêm PII de rede de apoio → cifrados.
    plano_seguranca_cifrado: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    observacoes_cifrado: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)

    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
