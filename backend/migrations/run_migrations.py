"""Runner ad-hoc de migrações — aplica scripts NNN_*.sql em ordem.

Uso:
    uv run python migrations/run_migrations.py

Idempotente: cada arquivo aplicado é registrado em `_schema_migrations`.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

# Carrega DATABASE_URL do backend/.env se existir.
BACKEND_ROOT = Path(__file__).resolve().parent.parent
DOTENV = BACKEND_ROOT / ".env"
if DOTENV.exists():
    for line in DOTENV.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

MIGRATIONS_DIR = BACKEND_ROOT / "migrations"
PATTERN = re.compile(r"^(\d{3})_[a-z0-9_]+\.sql$")


def _to_sync_dsn(url: str) -> str:
    """psycopg2 espera postgresql:// (não postgresql+asyncpg://)."""
    return url.replace("postgresql+asyncpg://", "postgresql://").replace(
        "postgresql+psycopg://", "postgresql://"
    )


def main() -> int:
    try:
        import psycopg2  # type: ignore
    except ImportError:
        # Fallback ao driver do sistema.
        print("psycopg2 não disponível no venv, tentando via `psql` do sistema.", file=sys.stderr)
        return _run_via_psql()

    dsn = _to_sync_dsn(os.environ["DATABASE_URL"])
    conn = psycopg2.connect(dsn)
    conn.autocommit = False
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS _schema_migrations (
            nome        TEXT PRIMARY KEY,
            aplicado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )
    conn.commit()

    files = sorted(f for f in MIGRATIONS_DIR.glob("*.sql") if PATTERN.match(f.name))
    for f in files:
        cur.execute("SELECT 1 FROM _schema_migrations WHERE nome = %s", (f.name,))
        if cur.fetchone():
            print(f"  [ok ] {f.name} (já aplicada)")
            continue
        print(f"  [run] {f.name}")
        sql = f.read_text()
        try:
            cur.execute(sql)
            cur.execute(
                "INSERT INTO _schema_migrations(nome) VALUES (%s)", (f.name,)
            )
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"  [FAIL] {f.name}: {e}", file=sys.stderr)
            return 2

    cur.close()
    conn.close()
    print("Migrações concluídas.")
    return 0


def _run_via_psql() -> int:
    import shutil
    import subprocess
    from urllib.parse import urlparse

    if not shutil.which("psql"):
        print("psql não encontrado.", file=sys.stderr)
        return 3

    dsn = _to_sync_dsn(os.environ["DATABASE_URL"])
    parsed = urlparse(dsn)
    env = os.environ.copy()
    env["PGPASSWORD"] = parsed.password or ""
    base_args = [
        "psql",
        "-h", parsed.hostname or "127.0.0.1",
        "-p", str(parsed.port or 5432),
        "-U", parsed.username or "praxis_user",
        "-d", (parsed.path or "/praxis").lstrip("/") or "praxis",
        "-v", "ON_ERROR_STOP=1",
    ]
    subprocess.run(
        base_args + ["-c",
            "CREATE TABLE IF NOT EXISTS _schema_migrations (nome TEXT PRIMARY KEY, aplicado_em TIMESTAMPTZ NOT NULL DEFAULT NOW());"],
        env=env, check=True,
    )
    files = sorted(f for f in MIGRATIONS_DIR.glob("*.sql") if PATTERN.match(f.name))
    for f in files:
        r = subprocess.run(
            base_args + ["-tAc", f"SELECT 1 FROM _schema_migrations WHERE nome='{f.name}'"],
            env=env, check=True, capture_output=True, text=True,
        )
        if r.stdout.strip() == "1":
            print(f"  [ok ] {f.name} (já aplicada)")
            continue
        print(f"  [run] {f.name}")
        subprocess.run(base_args + ["-f", str(f)], env=env, check=True)
        subprocess.run(
            base_args + ["-c", f"INSERT INTO _schema_migrations(nome) VALUES ('{f.name}')"],
            env=env, check=True,
        )
    print("Migrações concluídas (via psql).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
