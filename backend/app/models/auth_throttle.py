from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class AuthThrottle(Base):
    """Contador de tentativas de autenticação por chave (conta ou IP).

    Chave: "acct:<email>" ou "ip:<ip>". Usado para lockout progressivo em
    login e 2FA. Persistente (sobrevive a restart do worker). Ver migração 018.
    """

    __tablename__ = "auth_throttle"

    chave: Mapped[str] = mapped_column(String(320), primary_key=True)
    falhas: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    primeira_falha: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ultima_falha: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    bloqueado_ate: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
