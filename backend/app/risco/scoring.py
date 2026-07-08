"""Estratificação determinística do rastreio C-SSRS — fonte única do nível.

Puro: sem IA, sem I/O. O nível é FACTUAL, derivado das respostas sim/não do
rastreio e do comportamento relatado, segundo a triagem padrão do protocolo
Columbia. A interpretação clínica final é sempre do profissional.

Triagem (do mais grave para o menos):
- ALTO    : intenção (q4), plano com intenção (q5) ou comportamento nos últimos 3 meses.
- MODERADO: pensou no método (q3), sem intenção/plano nem comportamento recente.
- BAIXO   : ideação (q1/q2) sem método/intenção/plano, ou comportamento apenas ao
            longo da vida (há mais de 3 meses).
- MÍNIMO  : sem ideação nem comportamento relatados.
"""
from __future__ import annotations

from typing import Any

NIVEIS = ("minimo", "baixo", "moderado", "alto")


def _flag(cssrs: dict[str, Any], item_id: str) -> bool:
    return bool(cssrs.get(item_id) is True)


def estratificar(cssrs: dict[str, Any]) -> dict[str, Any]:
    """Deriva o nível de risco e os itens que o justificam (transparência)."""
    cssrs = cssrs or {}
    comportamento = cssrs.get("comportamento_quando")  # "nao" | "vida" | "recente" | None
    gatilhos: list[str] = []

    if _flag(cssrs, "q4"):
        gatilhos.append("q4")
    if _flag(cssrs, "q5"):
        gatilhos.append("q5")
    if comportamento == "recente":
        gatilhos.append("comportamento_recente")

    if gatilhos:
        nivel = "alto"
    elif _flag(cssrs, "q3"):
        nivel = "moderado"
        gatilhos.append("q3")
    elif _flag(cssrs, "q1") or _flag(cssrs, "q2") or comportamento == "vida":
        nivel = "baixo"
        for iid in ("q1", "q2"):
            if _flag(cssrs, iid):
                gatilhos.append(iid)
        if comportamento == "vida":
            gatilhos.append("comportamento_vida")
    else:
        nivel = "minimo"

    return {"nivel": nivel, "gatilhos": gatilhos, "recomendacao": _recomendacao(nivel)}


# Orientação padrão por nível — factual, sem acionar nada automaticamente.
_RECOMENDACAO = {
    "alto": (
        "Risco alto. Não deixar a pessoa sozinha; avaliar necessidade de "
        "encaminhamento imediato a serviço de emergência/CAPS. Elaborar Plano de "
        "Segurança e restringir acesso a meios. Conduta é decisão do profissional."
    ),
    "moderado": (
        "Risco moderado. Elaborar Plano de Segurança, revisar acesso a meios e "
        "reavaliar em curto prazo. Conduta é decisão do profissional."
    ),
    "baixo": (
        "Risco baixo. Acompanhar, registrar Plano de Segurança e reavaliar. "
        "Conduta é decisão do profissional."
    ),
    "minimo": (
        "Sem ideação ou comportamento relatados neste rastreio. Manter "
        "acompanhamento de rotina. Conduta é decisão do profissional."
    ),
}


def _recomendacao(nivel: str) -> str:
    return _RECOMENDACAO.get(nivel, "")


# --- Sinal de risco para o Scribe -------------------------------------------
# Detector leve, factual, por palavra-chave. NÃO estratifica nem substitui o
# rastreio — apenas sugere ao profissional registrar uma avaliação formal quando
# o relato da sessão menciona risco.

_PALAVRAS_RISCO = (
    "suicíd", "suicid", "se matar", "tirar a própria vida", "tirar a vida",
    "acabar com tudo", "não quero mais viver", "nao quero mais viver",
    "vontade de morrer", "melhor estar morto", "melhor morrer",
    "autolesão", "autolesao", "me cortar", "se cortar", "me machucar",
    "ideação", "ideacao suicida", "tentativa de suicídio", "tentativa de suicidio",
)


def detectar_sinal_risco(texto: str | None) -> bool:
    if not texto:
        return False
    t = texto.lower()
    return any(p in t for p in _PALAVRAS_RISCO)
