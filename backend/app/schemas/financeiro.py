from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ReciboRefOut(BaseModel):
    id: str
    numero: int


class LancamentoOut(BaseModel):
    """Sessão realizada com valor — status de pagamento derivado (pendente|pago)."""
    sessao_id: str
    paciente_id: str
    paciente_nome: str
    data: datetime
    valor_centavos: int
    status: Literal["pendente", "pago"]
    forma: str | None
    pago_em: datetime | None
    recibo: ReciboRefOut | None


class PagarIn(BaseModel):
    forma: Literal["pix", "dinheiro", "cartao", "transferencia"]
    pago_em: datetime | None = None  # ausente → agora (UTC)


class PagamentoOut(BaseModel):
    id: str
    sessao_id: str
    valor_centavos: int
    status: str
    forma: str | None
    pago_em: datetime | None
    recibo_id: str | None


class ReciboIn(BaseModel):
    sessao_id: str


class ReciboOut(BaseModel):
    id: str
    numero: int
    paciente_id: str
    paciente_nome: str
    valor_centavos: int
    emitido_em: datetime
    anexo_id: str | None
