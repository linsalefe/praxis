from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    acao: Mapped[str] = mapped_column(String(32), nullable=False)  # ex.: LOGIN, LOGIN_2FA, CREATE, UPDATE, DELETE, VIEW, EXPORT, SIGN
    entidade: Mapped[str] = mapped_column(String(64), nullable=False)  # ex.: Paciente, Sessao, Evolucao
    entidade_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    ip: Mapped[str | None] = mapped_column(INET, nullable=True)
    meta: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
