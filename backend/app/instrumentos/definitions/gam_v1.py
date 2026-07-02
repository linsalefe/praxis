"""GAM — Gestão Autônoma da Medicação (Guia GAM-BR).

Estrutura pública em 6 passos, com perguntas escritas em PT-BR pelo CENAT
(paráfrase, sem transcrição do Guia original). O GAM digital é ferramenta de
**gestão autônoma e decisão compartilhada** — apoio à experiência da pessoa com
a medicação. NÃO é conduta medicamentosa: o psicólogo não prescreve, e a saída
nunca sugere dose, desmame, retirada ou troca. A decisão sobre medicação é do
usuário com o seu prescritor.

Baseado em: Guia da Gestão Autônoma da Medicação — GAM (adaptação brasileira,
UFRJ/UFF/UNICAMP/UFRGS).
"""

GAM_V1 = {
    "tipo": "gam",
    "versao": "v1",
    "titulo": "GAM — Gestão Autônoma da Medicação",
    "descricao": (
        "Instrumento de apoio à autonomia e à decisão compartilhada sobre o uso "
        "de medicamentos psiquiátricos. Registra a experiência da pessoa com a "
        "medicação e organiza temas para conversar com o prescritor. Não é "
        "prescrição nem orientação de conduta medicamentosa — a decisão é do "
        "usuário com o seu médico. Preenchimento assistido ao longo de encontros."
    ),
    "fonte": (
        "Estrutura baseada no Guia da Gestão Autônoma da Medicação — GAM "
        "(adaptação brasileira UFRJ/UFF/UNICAMP/UFRGS). Perguntas paráfrase por "
        "CENAT. Apoio à decisão compartilhada — não conduta medicamentosa."
    ),
    "definicao": {
        "secoes": [
            {
                "id": "voce_vida_direitos",
                "titulo": "1. Você, sua vida e seus direitos",
                "descricao": "Quem é você, o que dá sentido ao seu dia e a que você tem direito no cuidado.",
                "perguntas": [
                    {"id": "quem_sou", "tipo": "textarea",
                     "label": "Como você descreveria sua vida e o que é importante para você hoje?"},
                    {"id": "qualidade_vida", "tipo": "textarea",
                     "label": "O que te faz sentir bem e com qualidade de vida?"},
                    {"id": "direitos_cuidado", "tipo": "textarea",
                     "label": "O que você espera e a que sente ter direito no seu cuidado em saúde?"},
                ],
            },
            {
                "id": "experiencia_medicacao",
                "titulo": "2. Sua experiência com os medicamentos psiquiátricos",
                "descricao": "A história do seu uso de medicação e os sentidos que ela tem para você. (Registro da experiência — não avaliação de conduta.)",
                "perguntas": [
                    {"id": "historia_uso", "tipo": "textarea",
                     "label": "Como foi sua história com os medicamentos psiquiátricos até aqui?"},
                    {"id": "sentido_medicacao", "tipo": "textarea",
                     "label": "Que sentido a medicação tem na sua vida (o que representa para você)?"},
                    {"id": "como_foi_decidido", "tipo": "textarea",
                     "label": "Como as decisões sobre sua medicação costumam ser tomadas? Você participa delas?"},
                ],
            },
            {
                "id": "conhecendo_e_sentindo",
                "titulo": "3. Conhecendo os medicamentos e o que você sente",
                "descricao": "O que você usa e como percebe os efeitos no corpo, no humor e no dia a dia.",
                "perguntas": [
                    {"id": "o_que_uso", "tipo": "textarea",
                     "label": "Quais medicamentos você usa hoje, do jeito que você os conhece?"},
                    {"id": "efeitos_percebidos", "tipo": "textarea",
                     "label": "O que você percebe no corpo, no humor e na rotina desde que os usa?"},
                    {"id": "duvidas_sobre_remedios", "tipo": "textarea",
                     "label": "Que dúvidas você tem sobre os medicamentos que toma?"},
                ],
            },
            {
                "id": "beneficios_incomodos",
                "titulo": "4. Benefícios e incômodos percebidos",
                "descricao": "Na sua visão, o que a medicação ajuda e o que atrapalha.",
                "perguntas": [
                    {"id": "o_que_ajuda", "tipo": "textarea",
                     "label": "O que a medicação te ajuda a fazer ou a sentir?"},
                    {"id": "o_que_incomoda", "tipo": "textarea",
                     "label": "O que te incomoda ou atrapalha no uso da medicação?"},
                    {"id": "bem_estar_subjetivo", "tipo": "escala",
                     "label": "No geral, como você avalia seu bem-estar hoje? (0 = muito mal; 10 = muito bem)"},
                ],
            },
            {
                "id": "autonomia_rede",
                "titulo": "5. Fortalecendo a autonomia e a rede de apoio",
                "descricao": "Estratégias próprias, pessoas de confiança e projeto de vida.",
                "perguntas": [
                    {"id": "estrategias_proprias", "tipo": "textarea",
                     "label": "Que estratégias você já usa para se cuidar (além da medicação)?"},
                    {"id": "rede_apoio", "tipo": "textarea",
                     "label": "Quem faz parte da sua rede de apoio e como pode te ajudar?"},
                    {"id": "projeto_vida", "tipo": "textarea",
                     "label": "O que você gostaria de construir ou retomar na sua vida?"},
                ],
            },
            {
                "id": "dialogo_prescritor",
                "titulo": "6. Diálogo com o prescritor",
                "descricao": "As dúvidas e os temas que você quer levar ao seu médico/prescritor. (A decisão sobre medicação é sua, junto com o prescritor.)",
                "perguntas": [
                    {"id": "duvidas_para_medico", "tipo": "textarea",
                     "label": "Que dúvidas ou preocupações você quer conversar com o seu prescritor?"},
                    {"id": "o_que_quero_entender", "tipo": "textarea",
                     "label": "O que você gostaria de entender melhor sobre o seu tratamento?"},
                    {"id": "como_quero_participar", "tipo": "textarea",
                     "label": "Como você gostaria de participar das decisões sobre o seu cuidado?"},
                ],
            },
        ]
    },
}
