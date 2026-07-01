"""WRAP — Wellness Recovery Action Plan (versão CENAT).

Estrutura pública em 6 blocos, com perguntas escritas em PT-BR pelo CENAT
(paráfrase, sem transcrição do material original de Mary Ellen Copeland /
Copeland Center). O plano final é gerado como rascunho editável.

Baseado em: COPELAND, M. E. Wellness Recovery Action Plan. 1997.
"""

WRAP_V1 = {
    "tipo": "wrap",
    "versao": "v1",
    "titulo": "WRAP — Plano de Ação para Bem-estar e Recuperação",
    "descricao": (
        "Construtor de plano pessoal de bem-estar, atenção a sinais de alerta "
        "e crise. Preenchimento pode ser feito em conjunto com o(a) paciente."
    ),
    "fonte": (
        "Estrutura baseada no WRAP (Copeland, 1997). Perguntas paráfrase por CENAT."
    ),
    "definicao": {
        "secoes": [
            {
                "id": "bem_estar",
                "titulo": "1. Como é estar bem — caixa de ferramentas de bem-estar",
                "descricao": "Retrato do funcionamento saudável e ferramentas de manutenção.",
                "perguntas": [
                    {"id": "como_e_bem", "tipo": "textarea",
                     "label": "Descreva como é estar bem (sono, humor, energia, relações, rotina)"},
                    {"id": "praticas_diarias", "tipo": "textarea",
                     "label": "O que você faz para se manter bem no dia a dia?"},
                    {"id": "praticas_extras", "tipo": "textarea",
                     "label": "Práticas que fazem bem mas nem sempre lembra de fazer"},
                ],
            },
            {
                "id": "gatilhos",
                "titulo": "2. Gatilhos e como responder a eles",
                "descricao": "Situações que costumam desestabilizar e ações preventivas.",
                "perguntas": [
                    {"id": "meus_gatilhos", "tipo": "textarea",
                     "label": "Quais são seus gatilhos conhecidos?"},
                    {"id": "plano_gatilhos", "tipo": "textarea",
                     "label": "O que você faz quando um gatilho aparece?"},
                    {"id": "quem_ajuda_gatilho", "tipo": "textarea",
                     "label": "Quem pode te ajudar nesses momentos e como?"},
                ],
            },
            {
                "id": "sinais_alerta",
                "titulo": "3. Sinais de alerta precoces",
                "descricao": "Mudanças sutis que indicam que algo está começando a piorar.",
                "perguntas": [
                    {"id": "meus_sinais", "tipo": "textarea",
                     "label": "Quais são seus sinais precoces (mudança de sono, isolamento, irritabilidade, etc.)?"},
                    {"id": "plano_sinais", "tipo": "textarea",
                     "label": "O que você faz assim que percebe esses sinais?"},
                ],
            },
            {
                "id": "quando_piora",
                "titulo": "4. Quando as coisas pioram",
                "descricao": "Sinais claros de deterioração e resposta reforçada.",
                "perguntas": [
                    {"id": "sinais_piora", "tipo": "textarea",
                     "label": "Como você sabe que está piorando (sinais mais evidentes)?"},
                    {"id": "resposta_piora", "tipo": "textarea",
                     "label": "Que ações mais fortes você toma agora?"},
                    {"id": "quem_acionar_piora", "tipo": "textarea",
                     "label": "Quem você aciona nesse momento e como?"},
                ],
            },
            {
                "id": "crise",
                "titulo": "5. Plano de crise",
                "descricao": "Instruções para quem cuida quando você não consegue decidir.",
                "perguntas": [
                    {"id": "quando_perco_controle", "tipo": "textarea",
                     "label": "Como é para você quando 'perde o controle'? Como os outros percebem?"},
                    {"id": "pessoas_confiança", "tipo": "textarea",
                     "label": "Quem tem sua confiança para tomar decisões durante a crise?"},
                    {"id": "medicacoes_crise", "tipo": "textarea",
                     "label": "Medicações que funcionam bem para você (e as que devem ser evitadas)"},
                    {"id": "servicos_preferidos", "tipo": "textarea",
                     "label": "CAPS, hospitais, serviços preferidos (ou a evitar) e por quê"},
                    {"id": "o_que_ajuda", "tipo": "textarea",
                     "label": "O que ajuda a acalmar você durante a crise"},
                    {"id": "o_que_nao_ajuda", "tipo": "textarea",
                     "label": "O que NÃO ajuda ou piora"},
                ],
            },
            {
                "id": "pos_crise",
                "titulo": "6. Pós-crise — voltando para casa",
                "descricao": "Retomar rotina, revisar o plano, cuidar-se com gentileza.",
                "perguntas": [
                    {"id": "sinais_pos_crise", "tipo": "textarea",
                     "label": "Como você sabe que já pode retomar sua vida cotidiana?"},
                    {"id": "cuidados_pos_crise", "tipo": "textarea",
                     "label": "Cuidados especiais nas primeiras semanas após a crise"},
                    {"id": "revisar_plano", "tipo": "textarea",
                     "label": "O que você quer revisar ou ajustar neste WRAP a partir desta experiência?"},
                ],
            },
        ]
    },
}
