"""SRQ-20 — Self-Reporting Questionnaire (rastreio de transtornos mentais comuns).

Instrumento de uso livre da OMS (Harding et al., 1980). 20 itens Sim/Não
(Sim = 1); escore 0–20. Validação brasileira (Mari & Williams, 1986) adota
ponto de corte 7/8 — escore ≥ 7 indica rastreio positivo. Item 17 (ideação)
é sinal de alerta independentemente do escore.
"""

_OPCOES = [
    {"valor": 1, "rotulo": "Sim"},
    {"valor": 0, "rotulo": "Não"},
]

SRQ20_V1 = {
    "tipo": "srq20",
    "versao": "v1",
    "titulo": "SRQ-20 — Questionário de Autorrelato (rastreio)",
    "descricao": (
        "Vinte perguntas Sim/Não sobre os últimos 30 dias. Escore 0–20; ≥ 7 sugere "
        "rastreio positivo para transtorno mental comum. Rastreio, não diagnóstico. "
        "Escore factual; avaliação é do profissional."
    ),
    "fonte": (
        "SRQ-20 — Harding TW et al., World Health Organization (1980). Uso livre. "
        "Ponto de corte da validação brasileira (Mari JJ & Williams P, 1986)."
    ),
    "definicao": {
        "kind": "likert_sum",
        "instrucoes": "Nos últimos 30 dias:",
        "opcoes": _OPCOES,
        "itens": [
            {"id": "q1", "texto": "Você tem dores de cabeça frequentes?"},
            {"id": "q2", "texto": "Tem falta de apetite?"},
            {"id": "q3", "texto": "Dorme mal?"},
            {"id": "q4", "texto": "Assusta-se com facilidade?"},
            {"id": "q5", "texto": "Tem tremores nas mãos?"},
            {"id": "q6", "texto": "Sente-se nervoso(a), tenso(a) ou preocupado(a)?"},
            {"id": "q7", "texto": "Tem má digestão?"},
            {"id": "q8", "texto": "Tem dificuldade de pensar com clareza?"},
            {"id": "q9", "texto": "Tem se sentido triste ultimamente?"},
            {"id": "q10", "texto": "Tem chorado mais do que de costume?"},
            {"id": "q11", "texto": "Encontra dificuldade para realizar com satisfação suas atividades diárias?"},
            {"id": "q12", "texto": "Tem dificuldade para tomar decisões?"},
            {"id": "q13", "texto": "Tem dificuldade no trabalho (seu trabalho lhe causa sofrimento)?"},
            {"id": "q14", "texto": "É incapaz de desempenhar um papel útil em sua vida?"},
            {"id": "q15", "texto": "Tem perdido o interesse pelas coisas?"},
            {"id": "q16", "texto": "Você se sente uma pessoa inútil, sem préstimo?"},
            {"id": "q17", "texto": "Tem tido ideias de acabar com a vida?", "flag": "risco"},
            {"id": "q18", "texto": "Sente-se cansado(a) o tempo todo?"},
            {"id": "q19", "texto": "Tem sensações desagradáveis no estômago?"},
            {"id": "q20", "texto": "Você se cansa com facilidade?"},
        ],
        "faixas": [
            {"min": 0, "max": 6, "rotulo": "abaixo do ponto de corte", "severidade": "pos"},
            {"min": 7, "max": 20, "rotulo": "rastreio positivo — transtorno mental comum provável", "severidade": "warn"},
        ],
        "transformacao": None,
    },
}
