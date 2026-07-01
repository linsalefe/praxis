"""DASS-21 — Depression, Anxiety and Stress Scales (versão de 21 itens).

Escala de uso livre (Lovibond & Lovibond, 1995). 21 itens (0–3) divididos em
três subescalas de 7 itens (Depressão, Ansiedade, Estresse). Como a DASS-21 é
metade da DASS-42, cada soma de subescala é multiplicada por 2 antes de aplicar
os cutoffs oficiais. Versão em português (Vignola & Tucci, 2014).
"""

_OPCOES = [
    {"valor": 0, "rotulo": "Não se aplicou de forma alguma"},
    {"valor": 1, "rotulo": "Aplicou-se em algum grau, ou por pouco tempo"},
    {"valor": 2, "rotulo": "Aplicou-se em grau considerável, ou por boa parte do tempo"},
    {"valor": 3, "rotulo": "Aplicou-se muito, ou na maior parte do tempo"},
]

# Cutoffs oficiais (Lovibond & Lovibond, 1995) sobre o escore da subescala ×2.
_FAIXAS_DEP = [
    {"min": 0, "max": 9, "rotulo": "normal", "severidade": "pos"},
    {"min": 10, "max": 13, "rotulo": "leve", "severidade": "sage"},
    {"min": 14, "max": 20, "rotulo": "moderado", "severidade": "warn"},
    {"min": 21, "max": 27, "rotulo": "grave", "severidade": "warn-strong"},
    {"min": 28, "max": None, "rotulo": "extremamente grave", "severidade": "risk"},
]
_FAIXAS_ANS = [
    {"min": 0, "max": 7, "rotulo": "normal", "severidade": "pos"},
    {"min": 8, "max": 9, "rotulo": "leve", "severidade": "sage"},
    {"min": 10, "max": 14, "rotulo": "moderado", "severidade": "warn"},
    {"min": 15, "max": 19, "rotulo": "grave", "severidade": "warn-strong"},
    {"min": 20, "max": None, "rotulo": "extremamente grave", "severidade": "risk"},
]
_FAIXAS_EST = [
    {"min": 0, "max": 14, "rotulo": "normal", "severidade": "pos"},
    {"min": 15, "max": 18, "rotulo": "leve", "severidade": "sage"},
    {"min": 19, "max": 25, "rotulo": "moderado", "severidade": "warn"},
    {"min": 26, "max": 33, "rotulo": "grave", "severidade": "warn-strong"},
    {"min": 34, "max": None, "rotulo": "extremamente grave", "severidade": "risk"},
]

DASS21_V1 = {
    "tipo": "dass21",
    "versao": "v1",
    "titulo": "DASS-21 — Escalas de Depressão, Ansiedade e Estresse",
    "descricao": (
        "21 itens sobre a última semana, com três subescalas (Depressão, Ansiedade, "
        "Estresse). Cada subescala tem escore e faixa próprios. Escore factual; "
        "interpretação é do profissional."
    ),
    "fonte": (
        "DASS-21 — Lovibond SH & Lovibond PF (1995), Manual for the Depression Anxiety "
        "Stress Scales. Instrumento de uso livre. Versão em português (Vignola & Tucci, 2014)."
    ),
    "definicao": {
        "kind": "likert_sum",
        "instrucoes": (
            "Leia cada afirmação e indique o quanto ela se aplicou a você durante a "
            "última semana. Não há respostas certas ou erradas."
        ),
        "opcoes": _OPCOES,
        "itens": [
            {"id": "q1", "texto": "Achei difícil me acalmar", "subescala": "estresse"},
            {"id": "q2", "texto": "Senti minha boca seca", "subescala": "ansiedade"},
            {"id": "q3", "texto": "Não consegui vivenciar nenhum sentimento positivo", "subescala": "depressao"},
            {"id": "q4", "texto": "Tive dificuldade para respirar (ex.: respiração rápida ou falta de ar sem esforço físico)", "subescala": "ansiedade"},
            {"id": "q5", "texto": "Achei difícil ter iniciativa para fazer as coisas", "subescala": "depressao"},
            {"id": "q6", "texto": "Tive tendência a reagir de forma exagerada às situações", "subescala": "estresse"},
            {"id": "q7", "texto": "Senti tremores (ex.: nas mãos)", "subescala": "ansiedade"},
            {"id": "q8", "texto": "Senti que estava usando muita energia nervosa", "subescala": "estresse"},
            {"id": "q9", "texto": "Preocupei-me com situações em que eu pudesse entrar em pânico e parecer ridículo(a)", "subescala": "ansiedade"},
            {"id": "q10", "texto": "Senti que não tinha nada a desejar ou esperar do futuro", "subescala": "depressao"},
            {"id": "q11", "texto": "Percebi-me agitado(a)", "subescala": "estresse"},
            {"id": "q12", "texto": "Achei difícil relaxar", "subescala": "estresse"},
            {"id": "q13", "texto": "Senti-me desanimado(a) e triste", "subescala": "depressao"},
            {"id": "q14", "texto": "Fui intolerante com aquilo que me impedia de continuar o que eu estava fazendo", "subescala": "estresse"},
            {"id": "q15", "texto": "Senti que estava quase entrando em pânico", "subescala": "ansiedade"},
            {"id": "q16", "texto": "Não consegui me entusiasmar com nada", "subescala": "depressao"},
            {"id": "q17", "texto": "Senti que não tinha muito valor como pessoa", "subescala": "depressao"},
            {"id": "q18", "texto": "Senti que estava um tanto sensível ou emotivo(a) demais", "subescala": "estresse"},
            {"id": "q19", "texto": "Percebi as batidas do meu coração sem ter feito esforço físico (ex.: sensação de aumento ou falha dos batimentos)", "subescala": "ansiedade"},
            {"id": "q20", "texto": "Senti medo sem motivo", "subescala": "ansiedade"},
            {"id": "q21", "texto": "Senti que a vida não tinha sentido", "subescala": "depressao"},
        ],
        "subescalas": [
            {"id": "depressao", "rotulo": "Depressão", "multiplicador": 2,
             "itens": ["q3", "q5", "q10", "q13", "q16", "q17", "q21"], "faixas": _FAIXAS_DEP},
            {"id": "ansiedade", "rotulo": "Ansiedade", "multiplicador": 2,
             "itens": ["q2", "q4", "q7", "q9", "q15", "q19", "q20"], "faixas": _FAIXAS_ANS},
            {"id": "estresse", "rotulo": "Estresse", "multiplicador": 2,
             "itens": ["q1", "q6", "q8", "q11", "q12", "q14", "q18"], "faixas": _FAIXAS_EST},
        ],
        "transformacao": None,
    },
}
