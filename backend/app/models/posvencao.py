from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, LargeBinary, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class RegistroPosvencao(Base):
    """Registro de posvenção — cuidado prestado após uma morte por suicídio.

    Fecha o módulo de risco (Onda 1.1): acolhimento dos enlutados, comunicação
    segura, articulação da rede, cuidado com a equipe e acompanhamento do luto.
    Registro de apoio à decisão clínica, sem alerta/monitoramento automático.

    `paciente_id` é a âncora (enlutado em acompanhamento ou o próprio paciente
    falecido). O plano de posvenção e as observações contêm PII de terceiros
    (enlutados) → cifrados em repouso, como o Plano de Segurança.
    """

    __tablename__ = "registros_posvencao"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    paciente_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("pacientes.id", ondelete="RESTRICT"), nullable=False, index=True)
    criado_por: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)

    # Data do óbito.
    ocorrido_em: Mapped[date] = mapped_column(Date, nullable=False)
    # Vínculo da pessoa falecida com o paciente-âncora (fonte única: app/risco/posvencao.py).
    vinculo_perda: Mapped[str] = mapped_column(String(24), nullable=False)
    # Andamento do processo de posvenção (é contínuo, não pontual).
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="aberto")

    # Passos do protocolo (dict passo_id -> texto) e observações contêm PII de
    # enlutados → cifrados em repouso (Fernet).
    plano_posvencao_cifrado: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    observacoes_cifrado: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)

    registrado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
