from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class TokenRevogado(Base):
    """Blocklist de JWT por `jti` (revogação server-side).

    Um token cujo `jti` está aqui é rejeitado no `deps._load_user`. Usado no
    logout (revoga a sessão atual). Entradas só importam até o `exp` do token
    (TTL curto + teto de 12h) — purga periódica opcional. Ver migração 020.
    """

    __tablename__ = "token_revogado"

    jti: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    revogado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    motivo: Mapped[str | None] = mapped_column(Text, nullable=True)
