"""Instrumento de Redução de Danos (Onda 2.5) — testes puros da definição e do
registro no catálogo (o catálogo é semeado no startup, fora do escopo do teste de
API; a saída usa LLM, também fora do teste)."""
from app.instrumentos.definitions import CATALOGO, QUALITATIVOS, RD_V1
from app.instrumentos.geradores import _flatten_respostas, sintetizar_rd


def test_rd_registrado_no_catalogo():
    assert RD_V1 in CATALOGO
    assert RD_V1 in QUALITATIVOS
    assert RD_V1["tipo"] == "rd"
    # É qualitativo (secoes), não escala Likert.
    assert "secoes" in RD_V1["definicao"]
    assert "kind" not in RD_V1["definicao"]


def test_rd_tem_secoes_esperadas():
    ids = {s["id"] for s in RD_V1["definicao"]["secoes"]}
    assert {"uso_atual", "estrategias_rd", "metas_pactuadas", "vinculo_rede"} <= ids
    # Toda pergunta tem id, tipo e label.
    for sec in RD_V1["definicao"]["secoes"]:
        for p in sec["perguntas"]:
            assert p["id"] and p["tipo"] and p["label"]


def test_flatten_respostas_do_rd():
    respostas = {"uso_atual": {"substancias": "álcool nos fins de semana"}}
    texto = _flatten_respostas(RD_V1["definicao"], respostas)
    assert "álcool nos fins de semana" in texto
    assert "1. Uso atual" in texto


def test_gerador_rd_existe():
    # O gerador está disponível para o despacho do /gerar-saida.
    assert callable(sintetizar_rd)
