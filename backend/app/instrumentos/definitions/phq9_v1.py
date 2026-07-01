"""PHQ-9 — Patient Health Questionnaire (depressão).

Escala de uso livre (Kroenke, Spitzer & Williams, 2001; Pfizer disponibiliza
sem custo). Escore 0–27 por soma dos 9 itens (0–3). Item 9 (ideação) é um
sinal de alerta clínico independentemente do escore total.
"""

_OPCOES = [
    {"valor": 0, "rotulo": "Nenhuma vez"},
    {"valor": 1, "rotulo": "Vários dias"},
    {"valor": 2, "rotulo": "Mais da metade dos dias"},
    {"valor": 3, "rotulo": "Quase todos os dias"},
]

PHQ9_V1 = {
    "tipo": "phq9",
    "versao": "v1",
    "titulo": "PHQ-9 — Questionário de Saúde do Paciente (depressão)",
    "descricao": (
        "Rastreio de sintomas depressivos nas últimas 2 semanas. Escore de 0 a 27 "
        "com faixa de severidade calculada. O escore é factual; a interpretação "
        "clínica é do profissional."
    ),
    "fonte": (
        "PHQ-9 — Kroenke K, Spitzer RL, Williams JBW (2001). Instrumento de uso "
        "livre disponibilizado pela Pfizer. Versão em português."
    ),
    "definicao": {
        "kind": "likert_sum",
        "instrucoes": (
            "Nas últimas 2 semanas, com que frequência você foi incomodado(a) "
            "por algum dos problemas abaixo?"
        ),
        "opcoes": _OPCOES,
        "itens": [
            {"id": "q1", "texto": "Pouco interesse ou pouco prazer em fazer as coisas"},
            {"id": "q2", "texto": "Se sentir para baixo, deprimido(a) ou sem perspectiva"},
            {"id": "q3", "texto": "Dificuldade para pegar no sono, permanecer dormindo ou dormir demais"},
            {"id": "q4", "texto": "Se sentir cansado(a) ou com pouca energia"},
            {"id": "q5", "texto": "Falta de apetite ou comendo demais"},
            {"id": "q6", "texto": "Se sentir mal consigo mesmo(a) — ou achar que é um fracasso ou que decepcionou sua família ou a si mesmo(a)"},
            {"id": "q7", "texto": "Dificuldade para se concentrar nas coisas, como ler o jornal ou ver televisão"},
            {"id": "q8", "texto": "Lentidão para se movimentar ou falar (a ponto de outras pessoas notarem) — ou o oposto, estar tão agitado(a) que fica andando de um lado para o outro muito mais que o normal"},
            {"id": "q9", "texto": "Pensar em se ferir de alguma maneira ou que seria melhor estar morto(a)", "flag": "risco"},
        ],
        "faixas": [
            {"min": 0, "max": 4, "rotulo": "mínimo", "severidade": "pos"},
            {"min": 5, "max": 9, "rotulo": "leve", "severidade": "sage"},
            {"min": 10, "max": 14, "rotulo": "moderado", "severidade": "warn"},
            {"min": 15, "max": 19, "rotulo": "moderadamente grave", "severidade": "warn-strong"},
            {"min": 20, "max": 27, "rotulo": "grave", "severidade": "risk"},
        ],
        "transformacao": None,
    },
}
