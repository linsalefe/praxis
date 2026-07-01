from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, LargeBinary, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Paciente(Base):
    __tablename__ = "pacientes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True)

    # PII cifrada em repouso (Fernet AEAD).
    nome_cifrado: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    contato_cifrado: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    nascimento_cifrado: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    documento_cifrado: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)

    # Metadados não sensíveis (para busca/estatística).
    sexo: Mapped[str | None] = mapped_column(String(16), nullable=True)

    criado_por: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Soft-delete respeitando prazo de guarda.
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reter_ate: Mapped[date | None] = mapped_column(Date, nullable=True)
