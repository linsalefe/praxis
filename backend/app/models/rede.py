from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, LargeBinary, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class MembroRede(Base):
    """Membro da rede de apoio de um caso (genograma/ecomapa, Onda 2.3).

    Pessoa da família ou de serviços/comunidade ligada à pessoa cuidada, com tipo
    e força do vínculo. Nome cifrado (PII de terceiro). Pendura no caso → herda o
    sigilo por profissional do caso.
    """

    __tablename__ = "membros_rede"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    caso_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("casos.id", ondelete="CASCADE"), nullable=False, index=True)
    criado_por: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)

    nome_cifrado: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    papel: Mapped[str | None] = mapped_column(Text, nullable=True)
    tipo_vinculo: Mapped[str] = mapped_column(String(16), nullable=False, default="outro")  # familiar|comunitario|servico|outro
    forca_vinculo: Mapped[str] = mapped_column(String(16), nullable=False, default="forte")  # forte|fragil|conflito
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)

    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
