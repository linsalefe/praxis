"""Geração da sala de telessessão (provider-agnóstico).

Jitsi (default): a URL é determinística — o nome da sala é derivado por HMAC do
UUID da sessão com o segredo do servidor. Assim a sala é:
  - não-adivinhável: precisa do segredo (o UUID sozinho não deriva o nome);
  - sem PII: nem no nome nem na URL;
  - idempotente: mesma sessão → mesma sala.

Daily fica como extensão futura (criar room via API e devolver a URL do servidor);
por isso o retorno é só a URL — o chamador persiste em `sessoes.sala_url`.
"""
from __future__ import annotations

import hashlib
import hmac

from app.config import get_settings


def _nome_sala(sessao_id: str, secret: str) -> str:
    dig = hmac.new(secret.encode("utf-8"), str(sessao_id).encode("utf-8"), hashlib.sha256).hexdigest()
    return f"praxis-{dig[:32]}"


def gerar_sala_url(sessao_id: str) -> str:
    """URL da sala para a sessão. Determinística p/ Jitsi (idempotente)."""
    s = get_settings()
    if s.video_provider != "jitsi":
        raise ValueError(f"Provedor de vídeo não suportado: {s.video_provider}")
    nome = _nome_sala(sessao_id, s.jwt_secret)
    base = s.jitsi_base.rstrip("/")
    return f"{base}/{nome}"
