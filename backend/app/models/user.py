from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, LargeBinary, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    nome: Mapped[str] = mapped_column(String(160), nullable=False)
    crp: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # Verificação do CRP: formato é validado no cadastro; a confirmação contra a
    # base do CFP/CRP (quando houver integração) marca True. Ver migração 019.
    crp_verificado: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false", default=False)

    # Timbre profissional dos PDFs (Sprint W1) — todos opcionais, com fallback
    # para nome/crp quando vazios. Apenas apresentação nos documentos gerados.
    nome_exibicao: Mapped[str | None] = mapped_column(String(160), nullable=True)
    registro_profissional: Mapped[str | None] = mapped_column(String(64), nullable=True)
    contato_timbre: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # 'dialogo_aberto' | 'ouvir_vozes' | 'gam' | 'ptmf' | 'wrap' | 'reducao_danos' | 'outros'
    abordagem: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # 'owner' | 'profissional'
    papel: Mapped[str] = mapped_column(String(16), nullable=False, default="profissional")

    totp_secret_cifrado: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    totp_ativado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Revogação em massa (S3): a versão do token vai no claim `tv`. Tokens com
    # tv != token_versao são rejeitados. "Encerrar todas as sessões" incrementa.
    token_versao: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0", default=0)

    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
