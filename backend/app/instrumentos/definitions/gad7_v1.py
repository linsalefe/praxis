"""GAD-7 — Generalized Anxiety Disorder scale (ansiedade).

Escala de uso livre (Spitzer, Kroenke, Williams & Löwe, 2006; Pfizer). Escore
0–21 por soma dos 7 itens (0–3). Ponto de corte ≥10 sugere rastreio positivo.
"""

_OPCOES = [
    {"valor": 0, "rotulo": "Nenhuma vez"},
    {"valor": 1, "rotulo": "Vários dias"},
    {"valor": 2, "rotulo": "Mais da metade dos dias"},
    {"valor": 3, "rotulo": "Quase todos os dias"},
]

GAD7_V1 = {
    "tipo": "gad7",
    "versao": "v1",
    "titulo": "GAD-7 — Transtorno de Ansiedade Generalizada",
    "descricao": (
        "Rastreio de sintomas de ansiedade nas últimas 2 semanas. Escore de 0 a 21 "
        "com faixa de severidade calculada. Escore factual; interpretação é do "
        "profissional."
    ),
    "fonte": (
        "GAD-7 — Spitzer RL, Kroenke K, Williams JBW, Löwe B (2006). Instrumento de "
        "uso livre disponibilizado pela Pfizer. Versão em português."
    ),
    "definicao": {
        "kind": "likert_sum",
        "instrucoes": (
            "Nas últimas 2 semanas, com que frequência você foi incomodado(a) "
            "pelos seguintes problemas?"
        ),
        "opcoes": _OPCOES,
        "itens": [
            {"id": "q1", "texto": "Sentir-se nervoso(a), ansioso(a) ou muito tenso(a)"},
            {"id": "q2", "texto": "Não ser capaz de impedir ou de controlar as preocupações"},
            {"id": "q3", "texto": "Preocupar-se muito com diversas coisas"},
            {"id": "q4", "texto": "Dificuldade para relaxar"},
            {"id": "q5", "texto": "Ficar tão agitado(a) que se torna difícil permanecer sentado(a)"},
            {"id": "q6", "texto": "Ficar facilmente aborrecido(a) ou irritado(a)"},
            {"id": "q7", "texto": "Sentir medo como se algo horrível fosse acontecer"},
        ],
        "faixas": [
            {"min": 0, "max": 4, "rotulo": "mínimo", "severidade": "pos"},
            {"min": 5, "max": 9, "rotulo": "leve", "severidade": "sage"},
            {"min": 10, "max": 14, "rotulo": "moderado", "severidade": "warn"},
            {"min": 15, "max": 21, "rotulo": "grave", "severidade": "risk"},
        ],
        "transformacao": None,
    },
}
