"""WHO-5 — Índice de Bem-Estar da OMS.

Escala de uso livre da OMS (1998, Psychiatric Research Unit, WHO Collaborating
Centre — uso livre com atribuição). 5 itens (0–5); soma bruta 0–25 é
multiplicada por 4 → escore 0–100. Aqui MAIOR = MELHOR bem-estar; escore baixo
sugere rastreio para depressão.
"""

_OPCOES = [
    {"valor": 5, "rotulo": "O tempo todo"},
    {"valor": 4, "rotulo": "A maior parte do tempo"},
    {"valor": 3, "rotulo": "Mais da metade do tempo"},
    {"valor": 2, "rotulo": "Menos da metade do tempo"},
    {"valor": 1, "rotulo": "De vez em quando"},
    {"valor": 0, "rotulo": "Em nenhum momento"},
]

WHO5_V1 = {
    "tipo": "who5",
    "versao": "v1",
    "titulo": "WHO-5 — Índice de Bem-Estar (OMS)",
    "descricao": (
        "Cinco afirmações sobre bem-estar nas últimas 2 semanas. Escore bruto (0–25) "
        "×4 = 0–100 (maior é melhor). Escore ≤ 50 sugere rastreio para depressão. "
        "Escore factual; interpretação é do profissional."
    ),
    "fonte": (
        "WHO-5 Well-Being Index — World Health Organization (1998), Psychiatric "
        "Research Unit, WHO Collaborating Centre, Hillerød. Uso livre com atribuição. "
        "Versão em português."
    ),
    "definicao": {
        "kind": "likert_sum",
        "instrucoes": (
            "Para cada afirmação, indique como você se sentiu nas últimas 2 semanas."
        ),
        "opcoes": _OPCOES,
        "itens": [
            {"id": "q1", "texto": "Eu me senti alegre e de bom humor"},
            {"id": "q2", "texto": "Eu me senti calmo(a) e relaxado(a)"},
            {"id": "q3", "texto": "Eu me senti ativo(a) e cheio(a) de energia"},
            {"id": "q4", "texto": "Eu me senti descansado(a) e revigorado(a) ao acordar"},
            {"id": "q5", "texto": "Meu dia a dia tem sido preenchido com coisas que me interessam"},
        ],
        # Faixas na escala transformada 0–100 (maior = melhor).
        "faixas": [
            {"min": 0, "max": 28, "rotulo": "bem-estar muito baixo — rastreio p/ depressão", "severidade": "risk"},
            {"min": 29, "max": 50, "rotulo": "bem-estar reduzido", "severidade": "warn"},
            {"min": 51, "max": 100, "rotulo": "bem-estar adequado", "severidade": "pos"},
        ],
        "transformacao": {"tipo": "x4", "escala": "0-100"},
    },
}
