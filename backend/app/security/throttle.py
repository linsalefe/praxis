"""Rate-limit / lockout de autenticação (login e 2FA).

Backed por tabela (`auth_throttle`), não Redis — o backend roda com 1 worker e
precisa que o bloqueio sobreviva a restart. Conta falhas por chave dentro de uma
janela; ao atingir o limiar, bloqueia por um tempo que cresce a cada nova falha
(backoff exponencial com teto). Sucesso zera o contador.

Chaves usadas nos fluxos: "acct:<email|user_id>" e "ip:<ip>". Verifica-se as
duas — brute-force distribuído bate no limite por conta; força-bruta de uma
conta só bate no limite por IP.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth_throttle import AuthThrottle

LIMIAR = 5  # falhas dentro da janela antes de começar a bloquear
JANELA = timedelta(minutes=15)  # sem falhas por este tempo → contador zera
BLOQUEIO_BASE_S = 60  # 1º bloqueio ao atingir o limiar
BLOQUEIO_MAX_S = 30 * 60  # teto do bloqueio


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _backoff_s(falhas: int) -> int:
    """Bloqueio progressivo: 1min, 2min, 4min… a partir do limiar, com teto."""
    extra = max(falhas - LIMIAR, 0)
    return min(BLOQUEIO_BASE_S * (2 ** extra), BLOQUEIO_MAX_S)


def chave_conta(identificador: str) -> str:
    return f"acct:{identificador.lower()}"


def chave_ip(ip: str | None) -> str:
    return f"ip:{ip or 'desconhecido'}"


async def verificar_bloqueio(session: AsyncSession, chaves: list[str]) -> None:
    """Levanta 429 (com Retry-After) se qualquer chave estiver bloqueada."""
    agora = _agora()
    for chave in chaves:
        row = await session.get(AuthThrottle, chave)
        if row and row.bloqueado_ate and row.bloqueado_ate > agora:
            retry = max(int((row.bloqueado_ate - agora).total_seconds()), 1)
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                f"Muitas tentativas. Tente novamente em {retry}s.",
                headers={"Retry-After": str(retry)},
            )


async def registrar_falha(session: AsyncSession, chaves: list[str]) -> None:
    """Incrementa o contador de cada chave e bloqueia ao atingir o limiar.

    Não faz commit — o chamador comita junto com o log de auditoria.
    """
    agora = _agora()
    for chave in chaves:
        row = await session.get(AuthThrottle, chave)
        if row is None:
            row = AuthThrottle(chave=chave, falhas=0)
            session.add(row)
        # Janela expirada desde a última falha → reinicia a contagem.
        if row.ultima_falha and (agora - row.ultima_falha) > JANELA:
            row.falhas = 0
            row.bloqueado_ate = None
        if row.falhas == 0:
            row.primeira_falha = agora
        row.falhas += 1
        row.ultima_falha = agora
        if row.falhas >= LIMIAR:
            row.bloqueado_ate = agora + timedelta(seconds=_backoff_s(row.falhas))


async def registrar_sucesso(session: AsyncSession, chaves: list[str]) -> None:
    """Zera o contador das chaves após autenticação bem-sucedida."""
    for chave in chaves:
        row = await session.get(AuthThrottle, chave)
        if row is not None:
            row.falhas = 0
            row.bloqueado_ate = None
            row.primeira_falha = None
            row.ultima_falha = None
