"""Motor determinístico de escalas Likert somadas (`kind: "likert_sum"`).

Puro: sem IA, sem rede, sem I/O. O escore e a faixa são FACTUAIS — saem da
soma real dos itens e dos cutoffs declarados no `definicao`. A IA (se entrar,
em `gerar-saida`) só redige uma leitura em cima do número; nunca o recalcula.

Formato de respostas: `respostas["itens"] = {"q1": 2, "q2": 0, ...}` (uma única
seção "itens", compatível com o merge por seção do endpoint `salvar`).
"""
from __future__ import annotations

from typing import Any


def _faixa_de(escore: int, faixas: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Primeira faixa cujo [min, max] contém o escore. `max` ausente = +∞."""
    for f in faixas:
        lo = f.get("min")
        hi = f.get("max")
        if lo is not None and escore < lo:
            continue
        if hi is not None and escore > hi:
            continue
        return f
    return None


def pontuar_likert(definicao: dict[str, Any], respostas: dict[str, Any]) -> dict[str, Any]:
    """Calcula escore/faixa de uma escala `likert_sum`.

    Retorna um dict no shape de `PontuacaoOut`. A faixa só é resolvida quando a
    escala (ou subescala) está **completa** — escore parcial não vira severidade.
    """
    itens_def: list[dict[str, Any]] = definicao.get("itens", []) or []
    opcoes: list[dict[str, Any]] = definicao.get("opcoes", []) or []
    valores_opcoes = [o.get("valor", 0) for o in opcoes]
    max_val = max(valores_opcoes) if valores_opcoes else 0

    respmap: dict[str, Any] = (respostas or {}).get("itens", {}) or {}

    def valor_item(item: dict[str, Any]) -> int | None:
        raw = respmap.get(item["id"])
        if raw is None or raw == "":
            return None
        try:
            v = int(raw)
        except (TypeError, ValueError):
            return None
        if item.get("invertido"):
            v = max_val - v
        return v

    valores: dict[str, int | None] = {it["id"]: valor_item(it) for it in itens_def}
    total_itens = len(itens_def)
    itens_respondidos = sum(1 for v in valores.values() if v is not None)
    completo = total_itens > 0 and itens_respondidos == total_itens

    # ---- escalas com subescalas (ex.: DASS-21) --------------------------
    subescalas = definicao.get("subescalas")
    if subescalas:
        subescores: list[dict[str, Any]] = []
        for sub in subescalas:
            ids = list(sub.get("itens", []))
            soma = sum(v for iid in ids if (v := valores.get(iid)) is not None)
            n_resp = sum(1 for iid in ids if valores.get(iid) is not None)
            n_total = len(ids)
            mult = sub.get("multiplicador", 1)
            escore = soma * mult
            sub_completo = n_total > 0 and n_resp == n_total
            faixa = _faixa_de(escore, sub.get("faixas", [])) if sub_completo else None
            subescores.append({
                "id": sub["id"],
                "rotulo": sub.get("rotulo", sub["id"]),
                "escore": escore,
                "itens_respondidos": n_resp,
                "total_itens": n_total,
                "completo": sub_completo,
                "faixa_rotulo": faixa["rotulo"] if faixa else None,
                "severidade": faixa["severidade"] if faixa else None,
            })
        return {
            "tipo": "subescalas",
            "escore": None,
            "escore_bruto": None,
            "transformado": None,
            "faixa_rotulo": None,
            "severidade": None,
            "itens_respondidos": itens_respondidos,
            "total_itens": total_itens,
            "completo": completo,
            "subescores": subescores,
        }

    # ---- escala de escore único ----------------------------------------
    soma = sum(v for v in valores.values() if v is not None)

    transf = definicao.get("transformacao")
    transformado: int | None = None
    escore_para_faixa = soma
    if transf and transf.get("tipo") == "x4":
        transformado = soma * 4
        escore_para_faixa = transformado

    faixa = _faixa_de(escore_para_faixa, definicao.get("faixas", [])) if completo else None
    return {
        "tipo": "unico",
        "escore": escore_para_faixa,
        "escore_bruto": soma,
        "transformado": transformado,
        "faixa_rotulo": faixa["rotulo"] if faixa else None,
        "severidade": faixa["severidade"] if faixa else None,
        "itens_respondidos": itens_respondidos,
        "total_itens": total_itens,
        "completo": completo,
        "subescores": [],
    }
