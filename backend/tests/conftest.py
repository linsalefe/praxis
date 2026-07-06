"""Infra de testes: banco isolado (praxis_test), migrações, client ASGI e
helpers de autenticação (com 2FA, que é obrigatório para rotas clínicas).

IMPORTANTE: o env é configurado ANTES de importar qualquer módulo do app, porque
`app.db` cria o engine no import a partir de DATABASE_URL. Variáveis de ambiente
têm precedência sobre o .env no pydantic-settings.
"""
from __future__ import annotations

import os
import urllib.parse as _up
from pathlib import Path

# --- Env ANTES de importar o app -------------------------------------------
_BACKEND = Path(__file__).resolve().parent.parent
_DOTENV = _BACKEND / ".env"
if _DOTENV.exists():
    for _line in _DOTENV.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

# Chaves determinísticas de teste (Fernet válida) — o banco de teste é vazio,
# não há dado cifrado com a chave de prod.
os.environ["PRAXIS_FIELD_KEY"] = "P41vG7oQh0nQhO0m9m9m9m9m9m9m9m9m9m9m9m9m9m8="
os.environ.setdefault("PRAXIS_JWT_SECRET", "test-jwt-secret-nao-usar-em-prod")
os.environ.setdefault("PRAXIS_ENV", "test")

# DATABASE_URL de teste: TEST_DATABASE_URL explícito (CI) ou troca do nome do db.
_test_dsn = os.environ.get("TEST_DATABASE_URL")
if not _test_dsn:
    _real = os.environ["DATABASE_URL"]
    _parsed = _up.urlparse(_real)
    _test_dsn = _parsed._replace(path="/praxis_test").geturl()
_dbname = _up.urlparse(_test_dsn).path.lstrip("/")
assert "test" in _dbname, f"Recusando rodar testes contra banco não-teste: {_dbname!r}"
os.environ["DATABASE_URL"] = _test_dsn

import pyotp  # noqa: E402
import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

# Agora sim: engine/app já apontam para o banco de teste.
from app.db import engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _migrar_banco_teste():
    """Aplica todas as migrações no banco de teste (uma vez por sessão)."""
    from migrations import run_migrations

    rc = run_migrations.main()
    assert rc == 0, "Falha ao migrar o banco de teste"
    yield


@pytest_asyncio.fixture(autouse=True)
async def _limpar_tabelas():
    """Trunca todas as tabelas de dados antes de cada teste (isolamento).

    Descarta o engine ao fim de cada teste: o pytest-asyncio usa um event loop
    por teste, e o pool async prenderia conexões ao loop anterior (fechado).
    """
    async with engine.begin() as conn:
        rows = await conn.execute(text(
            "SELECT tablename FROM pg_tables WHERE schemaname='public' "
            "AND tablename <> '_schema_migrations'"
        ))
        tabelas = [r[0] for r in rows]
        if tabelas:
            alvo = ", ".join(f'"{t}"' for t in tabelas)
            await conn.execute(text(f"TRUNCATE {alvo} RESTART IDENTITY CASCADE"))
    yield
    await engine.dispose()


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# --- Helpers de autenticação -----------------------------------------------

_seq = {"n": 0}


def _email_unico(prefixo: str = "user") -> str:
    _seq["n"] += 1
    return f"{prefixo}{_seq['n']}@example.com"


async def _ativar_2fa(client: AsyncClient, headers: dict) -> str:
    r = await client.post("/auth/2fa/setup", headers=headers)
    assert r.status_code == 200, r.text
    secret = _up.parse_qs(_up.urlparse(r.json()["otpauth_url"]).query)["secret"][0]
    r = await client.post("/auth/2fa/verify", headers=headers,
                          json={"codigo": pyotp.TOTP(secret).now()})
    assert r.status_code == 200, r.text
    return secret


@pytest_asyncio.fixture
async def criar_conta(client: AsyncClient):
    """Factory: cria conta (com 2FA ativo) e devolve dados + headers de sessão."""
    async def _factory(*, com_2fa: bool = True, email: str | None = None,
                       senha: str = "senha12345", crp: str = "06/123456",
                       tenant_nome: str = "Consultorio Teste") -> dict:
        email = email or _email_unico()
        r = await client.post("/auth/register", json={
            "nome": "Prof Teste", "email": email, "senha": senha,
            "crp": crp, "tenant_nome": tenant_nome,
        })
        assert r.status_code == 201, r.text
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        secret = None
        if com_2fa:
            secret = await _ativar_2fa(client, headers)
        return {"email": email, "senha": senha, "token": token, "headers": headers, "secret": secret}
    return _factory


@pytest_asyncio.fixture
async def conta(criar_conta):
    """Conta padrão pronta para uso clínico (2FA ativo)."""
    return await criar_conta()
