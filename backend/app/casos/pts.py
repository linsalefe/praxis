"""Seções do Projeto Terapêutico Singular (PTS) — fonte única do formulário.

Estrutura baseada nos quatro momentos do PTS (Ministério da Saúde): compreensão
ampliada do caso, metas pactuadas, ações e responsabilidades, e reavaliação.
Servida ao frontend por `GET /casos/pts/definicao`.

v1 (Onda 1.2): individual — o profissional preenche o PTS do seu caso. A
co-autoria pela equipe entra na Onda 2 (2.1).
"""
from __future__ import annotations

from typing import Any

PTS_SECOES: list[dict[str, str]] = [
    {"id": "compreensao", "titulo": "Compreensão do caso",
     "ajuda": "Diagnóstico situacional ampliado e singular: história, contexto, vínculos, recursos e vulnerabilidades."},
    {"id": "metas", "titulo": "Metas e objetivos",
     "ajuda": "Objetivos pactuados com a pessoa (e rede, quando houver), realistas e revisáveis."},
    {"id": "acoes", "titulo": "Ações e responsabilidades",
     "ajuda": "O que será feito, por quem e em que prazo. Inclui a própria pessoa e a rede de apoio."},
    {"id": "rede_apoio", "titulo": "Rede de apoio",
     "ajuda": "Pessoas, serviços e território envolvidos no cuidado (o genograma/ecomapa estruturado vem depois)."},
    {"id": "reavaliacao", "titulo": "Reavaliação",
     "ajuda": "Quando e como o projeto será revisto; critérios de progresso."},
]

PTS_SECAO_IDS = {s["id"] for s in PTS_SECOES}


def definicao() -> dict[str, Any]:
    return {"secoes": PTS_SECOES}
