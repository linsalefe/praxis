"""PTMF — Power Threat Meaning Framework (Estrutura Poder, Ameaça, Significado).

Estrutura pública organizada nas 4 perguntas nucleares (+2 integrativas), com
perguntas escritas em PT-BR pelo CENAT (paráfrase, sem transcrição do documento
original). A saída é uma **formulação narrativa não-diagnóstica** — o PTMF é uma
alternativa ao diagnóstico psiquiátrico: nunca gera rótulo de transtorno nem
"severidade".

Baseado em: JOHNSTONE, L.; BOYLE, M. et al. The Power Threat Meaning Framework.
British Psychological Society, 2018 (uso livre, com atribuição).
"""

PTMF_V1 = {
    "tipo": "ptmf",
    "versao": "v1",
    "titulo": "PTMF — Poder, Ameaça e Significado",
    "descricao": (
        "Instrumento de formulação narrativa baseado nas perguntas nucleares do "
        "Power Threat Meaning Framework. Constrói sentido sobre a experiência de "
        "sofrimento sem diagnóstico — o que aconteceu, como afetou, que sentido "
        "teve e o que a pessoa fez para sobreviver. Preenchimento em conjunto com "
        "o(a) paciente; a saída é um rascunho editável."
    ),
    "fonte": (
        "Estrutura baseada no Power Threat Meaning Framework (Johnstone & Boyle "
        "et al., British Psychological Society, 2018). Perguntas paráfrase por "
        "CENAT. Formulação não-diagnóstica."
    ),
    "definicao": {
        "secoes": [
            {
                "id": "o_que_aconteceu",
                "titulo": "1. O que aconteceu com você?",
                "descricao": "Como o poder operou (e opera) na sua vida — o que foi feito a você, o que faltou, o contexto.",
                "perguntas": [
                    {"id": "eventos", "tipo": "textarea",
                     "label": "O que aconteceu na sua vida que ajuda a entender o seu sofrimento?"},
                    {"id": "poder", "tipo": "textarea",
                     "label": "Como o poder operou na sua vida (o que foi feito a você, o que faltou, quem tinha controle)?"},
                ],
            },
            {
                "id": "como_afetou",
                "titulo": "2. Como isso te afetou?",
                "descricao": "Que ameaças essas experiências representaram para você.",
                "perguntas": [
                    {"id": "ameacas", "tipo": "textarea",
                     "label": "Como essas experiências te afetaram? Que ameaças elas representaram (à segurança, aos vínculos, à identidade)?"},
                ],
            },
            {
                "id": "que_sentido",
                "titulo": "3. Que sentido você deu a isso?",
                "descricao": "Os significados que você construiu sobre o que viveu e sobre si.",
                "perguntas": [
                    {"id": "significados", "tipo": "textarea",
                     "label": "Que sentido você deu a essas experiências? O que passou a acreditar sobre si e sobre o mundo?"},
                ],
            },
            {
                "id": "o_que_fez",
                "titulo": "4. O que você precisou fazer para sobreviver?",
                "descricao": "As respostas à ameaça — formas de proteção, enfrentamento e sobrevivência.",
                "perguntas": [
                    {"id": "respostas_ameaca", "tipo": "textarea",
                     "label": "O que você precisou fazer para lidar, se proteger ou sobreviver a tudo isso?"},
                ],
            },
            {
                "id": "pontos_fortes",
                "titulo": "5. Quais são seus pontos fortes e recursos?",
                "descricao": "Capacidades, apoios e recursos de poder acessíveis a você. (Pergunta integrativa do PTMF.)",
                "perguntas": [
                    {"id": "forcas", "tipo": "textarea",
                     "label": "Quais são suas forças, habilidades e apoios (pessoas, recursos, acessos)?"},
                ],
            },
            {
                "id": "sua_historia",
                "titulo": "6. Qual é a sua história?",
                "descricao": "A narrativa integrada que dá coerência ao conjunto. (Pergunta integrativa do PTMF.)",
                "perguntas": [
                    {"id": "narrativa", "tipo": "textarea",
                     "label": "Juntando tudo, como você contaria a sua história com suas próprias palavras?"},
                ],
            },
        ]
    },
}
