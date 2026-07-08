from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, LargeBinary, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class EncontroGrupo(Base):
    """Um encontro de grupo/oficina/assembleia (Onda 2.2).

    Não pertence a um único paciente — agrega vários participantes. Sigilo por
    profissional via `criado_por` (owner vê todos; profissional vê os seus).
    """

    __tablename__ = "encontros_grupo"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    criado_por: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)

    tipo: Mapped[str] = mapped_column(String(16), nullable=False)  # grupo | oficina | assembleia
    titulo: Mapped[str] = mapped_column(Text, nullable=False)
    data: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    local: Mapped[str | None] = mapped_column(Text, nullable=True)
    tema: Mapped[str | None] = mapped_column(Text, nullable=True)
    registro: Mapped[str | None] = mapped_column(Text, nullable=True)

    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class ParticipanteEncontro(Base):
    """Participante de um encontro: paciente registrado e/ou nome livre (cifrado)."""

    __tablename__ = "participantes_encontro"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    encontro_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("encontros_grupo.id", ondelete="CASCADE"), nullable=False, index=True)
    paciente_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("pacientes.id", ondelete="SET NULL"), nullable=True, index=True)
    nome_livre_cifrado: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    presente: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
