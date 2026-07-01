from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, LargeBinary, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class CertificadoAssinatura(Base):
    """Certificado A1 (.pfx PKCS#12) do profissional, cifrado em repouso (Fernet).

    A SENHA do certificado NUNCA é armazenada — é informada no ato de assinar.
    """
    __tablename__ = "certificados_assinatura"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)

    arquivo_cifrado: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    titular: Mapped[str] = mapped_column(Text, nullable=False)
    emissor: Mapped[str | None] = mapped_column(Text, nullable=True)
    validade_ate: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
