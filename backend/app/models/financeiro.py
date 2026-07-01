from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Pagamento(Base):
    __tablename__ = "pagamentos"
    __table_args__ = (UniqueConstraint("sessao_id", name="pagamentos_sessao_id_key"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    sessao_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sessoes.id", ondelete="CASCADE"), nullable=False)

    valor_centavos: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="pago")  # pendente | pago
    forma: Mapped[str | None] = mapped_column(String(16), nullable=True)             # pix|dinheiro|cartao|transferencia
    pago_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    recibo_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    criado_por: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Recibo(Base):
    __tablename__ = "recibos"
    __table_args__ = (UniqueConstraint("tenant_id", "numero", name="recibos_tenant_id_numero_key"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    numero: Mapped[int] = mapped_column(Integer, nullable=False)                     # sequencial por tenant
    paciente_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("pacientes.id", ondelete="RESTRICT"), nullable=False)
    sessao_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("sessoes.id", ondelete="SET NULL"), nullable=True)

    valor_centavos: Mapped[int] = mapped_column(Integer, nullable=False)
    emitido_por: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    emitido_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    anexo_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("anexos_prontuario.id", ondelete="SET NULL"), nullable=True)


class ReciboContador(Base):
    __tablename__ = "recibo_contadores"

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True)
    proximo: Mapped[int] = mapped_column(Integer, nullable=False)
