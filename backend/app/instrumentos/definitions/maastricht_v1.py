"""Entrevista de Maastricht — instrumento clínico digital.

Estrutura pública em 13 seções, com perguntas escritas em PT-BR pelo CENAT,
sem transcrição do manual original (que é protegido por copyright de
Romme & Escher). O resultado é uma **formulação clínica** — não um
diagnóstico — coerente com a abordagem Ouvir Vozes.

Baseado em: ROMME, M.; ESCHER, S. Making sense of voices. 2000.
"""

MAASTRICHT_V1 = {
    "tipo": "maastricht",
    "versao": "v1",
    "titulo": "Entrevista de Maastricht — formulação",
    "descricao": (
        "Instrumento estruturado para exploração da experiência de ouvir vozes. "
        "Preenchimento guiado seção a seção; ao final, o Práxis gera uma "
        "formulação clínica rascunho embasada no acervo, que o profissional "
        "revisa e finaliza."
    ),
    "fonte": (
        "Estrutura baseada na Entrevista de Maastricht (Romme & Escher, 2000). "
        "Perguntas paráfrase por CENAT."
    ),
    "definicao": {
        "secoes": [
            {
                "id": "info_pessoais",
                "titulo": "1. Informações pessoais e histórico",
                "descricao": "Contexto do encaminhamento e da primeira aparição das vozes.",
                "perguntas": [
                    {"id": "idade_inicio", "tipo": "integer",
                     "label": "Idade em que ouviu vozes pela primeira vez"},
                    {"id": "contexto_inicio", "tipo": "textarea",
                     "label": "O que estava acontecendo na vida quando as vozes começaram?"},
                    {"id": "encaminhamento", "tipo": "textarea",
                     "label": "Quem encaminhou / por que buscou apoio agora?"},
                ],
            },
            {
                "id": "caracteristicas",
                "titulo": "2. Características das vozes",
                "descricao": "Aspectos formais da experiência auditiva.",
                "perguntas": [
                    {"id": "quantidade", "tipo": "text",
                     "label": "Quantas vozes diferentes você identifica?"},
                    {"id": "sexo_idade", "tipo": "text",
                     "label": "Gênero, idade aparente e outras características das vozes"},
                    {"id": "de_onde_vem", "tipo": "select",
                     "label": "As vozes parecem vir de onde?",
                     "opcoes": ["dentro da cabeça", "de fora (ouvidas como som real)", "ambos", "não sei descrever"]},
                    {"id": "clareza", "tipo": "escala",
                     "label": "Quão claras/nítidas são as vozes? (1 = quase inaudíveis; 10 = totalmente claras)"},
                ],
            },
            {
                "id": "historia_pessoal",
                "titulo": "3. História pessoal de ouvir vozes",
                "descricao": "Como a relação com as vozes se transformou ao longo do tempo.",
                "perguntas": [
                    {"id": "frequencia_atual", "tipo": "select",
                     "label": "Com que frequência ouve vozes atualmente?",
                     "opcoes": ["várias vezes ao dia", "diariamente", "algumas vezes por semana", "menos de uma vez por semana"]},
                    {"id": "mudancas_ao_longo_tempo", "tipo": "textarea",
                     "label": "Como a experiência mudou ao longo dos anos?"},
                    {"id": "periodos_ausencia", "tipo": "textarea",
                     "label": "Já houve períodos sem vozes? O que estava acontecendo então?"},
                ],
            },
            {
                "id": "gatilhos",
                "titulo": "4. Gatilhos",
                "descricao": "Situações, emoções ou estados que ativam ou intensificam as vozes.",
                "perguntas": [
                    {"id": "gatilhos_situacionais", "tipo": "textarea",
                     "label": "Que situações costumam ativar ou intensificar as vozes?"},
                    {"id": "gatilhos_emocionais", "tipo": "textarea",
                     "label": "Que emoções antecedem ou acompanham as vozes?"},
                    {"id": "reduz_vozes", "tipo": "textarea",
                     "label": "O que costuma reduzir ou silenciar as vozes?"},
                ],
            },
            {
                "id": "conteudo",
                "titulo": "5. O que as vozes dizem",
                "descricao": "Conteúdo simbólico, temas, tom emocional.",
                "perguntas": [
                    {"id": "temas_recorrentes", "tipo": "textarea",
                     "label": "Quais são os temas ou frases recorrentes?"},
                    {"id": "tom_emocional", "tipo": "multiselect",
                     "label": "Tom predominante das vozes",
                     "opcoes": ["crítico/hostil", "acolhedor/protetor", "assustador", "neutro/comentador", "provocativo", "confuso"]},
                    {"id": "ordens", "tipo": "textarea",
                     "label": "As vozes dão ordens? Quais? Como você responde a elas?"},
                ],
            },
            {
                "id": "influencia_vida",
                "titulo": "6. Influência no cotidiano",
                "descricao": "Impacto funcional nas atividades e relações.",
                "perguntas": [
                    {"id": "impacto_trabalho", "tipo": "textarea",
                     "label": "Como as vozes impactam trabalho, estudo, cuidado pessoal?"},
                    {"id": "impacto_relacoes", "tipo": "textarea",
                     "label": "Impacto nas relações pessoais/familiares?"},
                    {"id": "grau_sofrimento", "tipo": "escala",
                     "label": "Grau de sofrimento associado às vozes hoje (0 = nenhum; 10 = insuportável)"},
                ],
            },
            {
                "id": "interpretacao",
                "titulo": "7. Interpretação da origem",
                "descricao": "O que a pessoa entende que as vozes são.",
                "perguntas": [
                    {"id": "explicacao_pessoal", "tipo": "textarea",
                     "label": "O que você acredita que as vozes são?"},
                    {"id": "explicacoes_recebidas", "tipo": "textarea",
                     "label": "Que explicações profissionais/familiares você já recebeu?"},
                ],
            },
            {
                "id": "relacao",
                "titulo": "8. Relação com as vozes",
                "descricao": "Modo de vínculo (poder, medo, negociação, aliança).",
                "perguntas": [
                    {"id": "quem_manda", "tipo": "select",
                     "label": "Quem está no comando na relação com as vozes?",
                     "opcoes": ["as vozes", "eu", "às vezes eu, às vezes elas", "não consigo definir"]},
                    {"id": "consegue_dialogar", "tipo": "boolean",
                     "label": "Você consegue dialogar/negociar com elas?"},
                    {"id": "postura", "tipo": "textarea",
                     "label": "Como descreveria sua postura atual com as vozes?"},
                ],
            },
            {
                "id": "enfrentamento",
                "titulo": "9. Estratégias de enfrentamento",
                "descricao": "O que a pessoa já usa (funcionando ou não).",
                "perguntas": [
                    {"id": "estrategias_atuais", "tipo": "textarea",
                     "label": "O que você faz hoje quando as vozes ficam intensas?"},
                    {"id": "estrategias_efetivas", "tipo": "textarea",
                     "label": "O que já tentou e funcionou?"},
                    {"id": "estrategias_prejudiciais", "tipo": "textarea",
                     "label": "O que tentou e piorou ou não ajudou?"},
                ],
            },
            {
                "id": "infancia",
                "titulo": "10. Experiências de infância e adolescência",
                "descricao": "Eventos significativos, vínculos, adversidades. Sem forçar detalhamento.",
                "perguntas": [
                    {"id": "familia_origem", "tipo": "textarea",
                     "label": "Como descreveria sua família de origem e os vínculos afetivos?"},
                    {"id": "eventos_marcantes", "tipo": "textarea",
                     "label": "Eventos marcantes (positivos ou adversos) que gostaria de trazer"},
                    {"id": "trauma_disponivel", "tipo": "textarea",
                     "label": "Se sentir seguro para compartilhar, há experiências difíceis relevantes?"},
                ],
            },
            {
                "id": "historico_medico",
                "titulo": "11. Histórico médico e de saúde mental",
                "descricao": "Diagnósticos anteriores, internações, medicações — sem juízo.",
                "perguntas": [
                    {"id": "diagnosticos_previos", "tipo": "textarea",
                     "label": "Diagnósticos ou hipóteses recebidos anteriormente"},
                    {"id": "internacoes", "tipo": "textarea",
                     "label": "Internações psiquiátricas (quando/porquê)"},
                    {"id": "medicacoes_atuais", "tipo": "textarea",
                     "label": "Medicações em uso atual e adesão"},
                ],
            },
            {
                "id": "rede_social",
                "titulo": "12. Rede social e recursos",
                "descricao": "Pessoas, grupos, serviços presentes na vida.",
                "perguntas": [
                    {"id": "vinculos_significativos", "tipo": "textarea",
                     "label": "Pessoas em quem você confia e que sabem sobre as vozes"},
                    {"id": "grupos_pares", "tipo": "textarea",
                     "label": "Participa de algum grupo (Ouvir Vozes, associação, comunidade)?"},
                    {"id": "servicos", "tipo": "textarea",
                     "label": "CAPS, UBS, outros serviços em uso"},
                ],
            },
            {
                "id": "objetivos",
                "titulo": "13. Objetivos e próximos passos",
                "descricao": "O que a pessoa quer construir a partir daqui.",
                "perguntas": [
                    {"id": "objetivos_pessoais", "tipo": "textarea",
                     "label": "Quais mudanças ou objetivos você gostaria de trabalhar?"},
                    {"id": "prioridades_curtas", "tipo": "textarea",
                     "label": "Uma ou duas prioridades para as próximas semanas"},
                ],
            },
        ]
    },
}
