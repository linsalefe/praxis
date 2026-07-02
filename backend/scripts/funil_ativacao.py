"""Funil de ativação — 4 marcos por conta (tenant), derivado do audit_log.

Read-only e cross-tenant: é uma métrica do operador (CENAT), por isso roda como
SCRIPT no servidor — nunca como endpoint (um endpoint cross-tenant furaria o
isolamento por tenant que o resto do sistema protege). Não escreve nada.

Marcos (primeiro timestamp por tenant, tudo factual do audit_log):
    ① criou paciente     CREATE       Paciente
    ② 1ª evolução        CREATE       Evolucao          (rascunho = ativação)
    ③ 1ª pergunta Sofia  SOFIA_ASK    SofiaQuery
    ④ 1º PDF clínico     ANEXO_CRIADO AnexoProntuario   (origem documento_cfp|resposta_instrumento; recibo NÃO conta)

Rodar:
    cd /opt/praxis/backend && python scripts/funil_ativacao.py          # tabela + agregado no stdout
    cd /opt/praxis/backend && python scripts/funil_ativacao.py --csv    # CSV (timestamps ISO) no stdout
"""
from __future__ import annotations

import asyncio
import csv
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# --- carrega .env do backend (mesmo padrão do ingest_acervo) -------------------
ROOT = Path(__file__).resolve().parent.parent
DOTENV = ROOT / ".env"
if DOTENV.exists():
    for line in DOTENV.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

sys.path.insert(0, str(ROOT))

from sqlalchemy import text  # noqa: E402

from app.db import SessionLocal  # noqa: E402

# Uma query, um MIN(ts) por marco via FILTER (Postgres). LEFT JOIN garante que
# contas sem nenhuma atividade também apareçam (denominador do funil).
FUNIL_SQL = text(
    """
    SELECT
        t.id::text     AS tenant_id,
        t.nome         AS nome,
        t.tipo         AS tipo,
        t.criado_em    AS criado_em,
        MIN(a.ts) FILTER (WHERE a.acao = 'CREATE'       AND a.entidade = 'Paciente')        AS m1,
        MIN(a.ts) FILTER (WHERE a.acao = 'CREATE'       AND a.entidade = 'Evolucao')        AS m2,
        MIN(a.ts) FILTER (WHERE a.acao = 'SOFIA_ASK'    AND a.entidade = 'SofiaQuery')      AS m3,
        MIN(a.ts) FILTER (WHERE a.acao = 'ANEXO_CRIADO' AND a.entidade = 'AnexoProntuario'
                          AND a.meta->>'origem_tipo' IN ('documento_cfp', 'resposta_instrumento')) AS m4
    FROM tenants t
    LEFT JOIN audit_log a ON a.tenant_id = t.id
    GROUP BY t.id, t.nome, t.tipo, t.criado_em
    ORDER BY t.criado_em
    """
)

MARCOS = ["① paciente", "② evolução", "③ Sofia", "④ PDF"]
KEYS = ["m1", "m2", "m3", "m4"]


async def carregar() -> list[dict]:
    async with SessionLocal() as session:
        rows = (await session.execute(FUNIL_SQL)).mappings().all()
    return [dict(r) for r in rows]


def no_primeiro_dia(ts: datetime | None, criado_em: datetime) -> bool:
    """True se o marco ocorreu em até 24h da criação da conta."""
    return ts is not None and ts <= criado_em + timedelta(days=1)


def ativou_ate_sofia_no_dia1(r: dict) -> bool:
    """①–③ todos presentes e todos dentro de 24h da criação da conta."""
    return all(no_primeiro_dia(r[k], r["criado_em"]) for k in ("m1", "m2", "m3"))


def _fmt(ts: datetime | None) -> str:
    return ts.strftime("%Y-%m-%d %H:%M") if ts else "—"


def _pct(num: int, den: int) -> str:
    return f"{(100 * num / den):.0f}%" if den else "—"


def imprimir_tabela(rows: list[dict]) -> None:
    print("\n=== Funil de ativação · por conta (tenant) ===")
    print("   marcos = primeiro registro real no audit_log; ✓ = atingido, — = não\n")
    cab = f"{'Conta':<26} {'Criada em':<16}  {'①':^3}{'②':^3}{'③':^3}{'④':^3}  {'①–③ ≤24h':>9}"
    print(cab)
    print("-" * len(cab))
    for r in rows:
        nome = (r["nome"] or "—")[:25]
        marcas = "".join(f"{'✓' if r[k] else '—':^3}" for k in KEYS)
        dia1 = "sim" if ativou_ate_sofia_no_dia1(r) else "não"
        print(f"{nome:<26} {_fmt(r['criado_em']):<16}  {marcas}  {dia1:>9}")


def imprimir_agregado(rows: list[dict]) -> None:
    n = len(rows)
    print(f"\n=== Agregado · {n} conta(s) ===\n")
    if n == 0:
        print("Nenhuma conta encontrada.")
        return

    atingiram = [sum(1 for r in rows if r[k] is not None) for k in KEYS]
    print("Atingiram cada marco (contas distintas):")
    for label, cnt in zip(MARCOS, atingiram):
        print(f"  {label:<13} {cnt:>3}/{n}  ({_pct(cnt, n)})")

    # Conversão ESTRITA: entre quem atingiu o marco anterior, quantos também
    # atingiram este (co-presença na MESMA conta — não a razão de contagens
    # totais, que misturaria contas diferentes).
    print("\nConversão sequencial (entre quem atingiu o marco anterior, na mesma conta):")
    for i in range(1, 4):
        prev = atingiram[i - 1]
        ambos = sum(1 for r in rows if r[KEYS[i - 1]] is not None and r[KEYS[i]] is not None)
        print(f"  {MARCOS[i - 1].split()[0]} → {MARCOS[i].split()[0]}   {ambos:>3}/{prev:<3} ({_pct(ambos, prev)})")

    completou_tudo = sum(1 for r in rows if all(r[k] is not None for k in KEYS))
    print(f"\n  ① → ④ (completou os 4)   {completou_tudo:>3}/{n}   ({_pct(completou_tudo, n)})")

    dia1 = sum(1 for r in rows if ativou_ate_sofia_no_dia1(r))
    print(f"  Ativação no 1º dia (①–③ ≤24h da criação): {dia1}/{n} ({_pct(dia1, n)})")
    print("\n  Leitura: onde a maioria para é onde o onboarding/produto falha.")


def imprimir_csv(rows: list[dict]) -> None:
    w = csv.writer(sys.stdout)
    w.writerow(["tenant_id", "nome", "tipo", "criado_em",
                "m1_paciente", "m2_evolucao", "m3_sofia", "m4_pdf", "ativou_1_3_no_dia1"])
    for r in rows:
        w.writerow([
            r["tenant_id"], r["nome"], r["tipo"],
            r["criado_em"].isoformat() if r["criado_em"] else "",
            *[(r[k].isoformat() if r[k] else "") for k in KEYS],
            "sim" if ativou_ate_sofia_no_dia1(r) else "não",
        ])


async def main() -> None:
    rows = await carregar()
    if "--csv" in sys.argv[1:]:
        imprimir_csv(rows)
    else:
        imprimir_tabela(rows)
        imprimir_agregado(rows)


if __name__ == "__main__":
    asyncio.run(main())
