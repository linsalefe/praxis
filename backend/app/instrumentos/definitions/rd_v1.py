"""RD — Redução de Danos: registro e plano (Onda 2.5).

Instrumento qualitativo (secoes) alinhado ao paradigma da Redução de Danos: parte
do uso REAL da pessoa, sem exigir abstinência, foca em uso mais seguro, metas
PACTUADAS (definidas pela pessoa, não impostas) e no vínculo/rede que sustentam o
cuidado. NÃO é avaliação moral nem escore de gravidade; a abstinência só aparece
se for escolha da própria pessoa.

Perguntas escritas em PT-BR pelo CENAT. Apoio à decisão clínica — a conduta é do
profissional; a decisão sobre o próprio uso é da pessoa.
"""

RD_V1 = {
    "tipo": "rd",
    "versao": "v1",
    "titulo": "Redução de Danos — registro e plano",
    "descricao": (
        "Registro do uso de álcool e outras drogas na lógica da Redução de Danos: "
        "parte do uso real, sem exigir abstinência, e organiza estratégias de uso "
        "mais seguro, metas pactuadas com a pessoa e a rede de apoio. Não é escore "
        "de gravidade nem avaliação moral. Preenchimento assistido ao longo de encontros."
    ),
    "fonte": (
        "Estrutura baseada nos princípios da Redução de Danos (Política do "
        "Ministério da Saúde; literatura de RD). Perguntas por CENAT. Apoio ao "
        "cuidado centrado na pessoa — não conduta prescritiva."
    ),
    "definicao": {
        "secoes": [
            {
                "id": "uso_atual",
                "titulo": "1. Uso atual",
                "descricao": "O uso real da pessoa, registrado sem julgamento — ponto de partida do cuidado.",
                "perguntas": [
                    {"id": "substancias", "tipo": "textarea",
                     "label": "Que substâncias a pessoa usa atualmente (do jeito que ela relata)?"},
                    {"id": "frequencia_via_contexto", "tipo": "textarea",
                     "label": "Com que frequência, por qual via e em que contextos costuma usar?"},
                    {"id": "funcao_uso", "tipo": "textarea",
                     "label": "Que função/sentido o uso tem na vida da pessoa (o que ele oferece)?"},
                ],
            },
            {
                "id": "riscos_danos",
                "titulo": "2. Riscos e danos percebidos",
                "descricao": "O que a própria pessoa percebe como risco ou dano — na sua perspectiva.",
                "perguntas": [
                    {"id": "o_que_preocupa", "tipo": "textarea",
                     "label": "O que preocupa a pessoa em relação ao seu uso (se algo preocupa)?"},
                    {"id": "danos_ja_vividos", "tipo": "textarea",
                     "label": "Que danos ou situações de risco já ocorreram (saúde, social, legal, relações)?"},
                ],
            },
            {
                "id": "estrategias_rd",
                "titulo": "3. Estratégias de uso mais seguro",
                "descricao": "O que a pessoa já faz para se proteger e o que pode ser fortalecido.",
                "perguntas": [
                    {"id": "ja_faz", "tipo": "textarea",
                     "label": "Que estratégias de proteção a pessoa já usa (ex.: não usar sozinha, insumos limpos, hidratação, testar dose)?"},
                    {"id": "a_fortalecer", "tipo": "textarea",
                     "label": "Que estratégias de uso mais seguro podem ser combinadas/fortalecidas?"},
                ],
            },
            {
                "id": "metas_pactuadas",
                "titulo": "4. Metas pactuadas",
                "descricao": "Objetivos definidos PELA pessoa (uso mais seguro, redução, pausa, abstinência se for escolha dela — nunca imposta).",
                "perguntas": [
                    {"id": "objetivo_pessoa", "tipo": "textarea",
                     "label": "O que a pessoa deseja em relação ao seu uso neste momento?"},
                    {"id": "metas", "tipo": "textarea",
                     "label": "Que metas foram pactuadas (concretas e revisáveis)?"},
                    {"id": "prontidao", "tipo": "escala",
                     "label": "Prontidão da pessoa para a mudança que ela deseja (0 = nada pronta; 10 = totalmente pronta)"},
                ],
            },
            {
                "id": "vinculo_rede",
                "titulo": "5. Vínculo e rede de apoio",
                "descricao": "O que sustenta o cuidado: vínculo, serviços e pessoas.",
                "perguntas": [
                    {"id": "rede_apoio", "tipo": "textarea",
                     "label": "Quem e quais serviços fazem parte da rede de apoio da pessoa?"},
                    {"id": "acesso_insumos", "tipo": "textarea",
                     "label": "A pessoa tem acesso a insumos de RD e a serviços de saúde quando precisa?"},
                    {"id": "proximos_passos", "tipo": "textarea",
                     "label": "Próximos passos combinados e quando reavaliar."},
                ],
            },
        ]
    },
}
