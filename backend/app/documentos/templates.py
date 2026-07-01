"""Templates dos 5 tipos de documento conforme Res. CFP 06/2019.

Cada template define:
- os blocos obrigatórios que o LLM deve preencher (chaves em `conteudo`)
- a extensão-alvo por bloco (em palavras)
- os placeholders permitidos (o server substitui após geração)

Placeholders universais:
- {{PACIENTE_NOME}}, {{PACIENTE_DOC}}, {{PACIENTE_NASC}}
- {{PROFISSIONAL_NOME}}, {{PROFISSIONAL_CRP}}
- {{DATA_EMISSAO}}
- {{FINALIDADE}}, {{DESTINATARIO}}
"""
from __future__ import annotations

TEMPLATES: dict[str, dict] = {
    "declaracao": {
        "titulo": "Declaração",
        "descricao": (
            "Documento simples que informa a ocorrência de um fato "
            "(comparecimento, participação, acompanhamento em curso)."
        ),
        "blocos": [
            {
                "id": "texto",
                "label": "Texto da declaração",
                "hint": (
                    "Um único parágrafo. Cite o comparecimento/participação "
                    "e a finalidade. Sem análise clínica."
                ),
                "palavras_alvo": (40, 120),
            },
        ],
    },
    "atestado": {
        "titulo": "Atestado psicológico",
        "descricao": (
            "Afirma o estado psicológico observado e, quando aplicável, "
            "recomendação de afastamento/aptidão."
        ),
        "blocos": [
            {
                "id": "estado",
                "label": "Estado psicológico observado",
                "hint": (
                    "Descrição objetiva do que foi observado nas sessões. "
                    "Sem diagnóstico nosológico e sem CID (atribuição médica)."
                ),
                "palavras_alvo": (60, 150),
            },
            {
                "id": "recomendacao",
                "label": "Recomendação",
                "hint": (
                    "Se aplicável: afastamento por X dias, apto para tal "
                    "atividade, necessidade de acompanhamento continuado."
                ),
                "palavras_alvo": (20, 80),
            },
        ],
    },
    "relatorio": {
        "titulo": "Relatório psicológico",
        "descricao": (
            "Documento detalhado com identificação, descrição da demanda, "
            "procedimento, análise e conclusão."
        ),
        "blocos": [
            {"id": "identificacao", "label": "Identificação",
             "hint": "Quem é o paciente (usar {{PACIENTE_NOME}}, {{PACIENTE_DOC}}, {{PACIENTE_NASC}}), quem é o solicitante, período do acompanhamento.",
             "palavras_alvo": (50, 120)},
            {"id": "descricao_demanda", "label": "Descrição da demanda",
             "hint": "Motivo do encaminhamento/consulta e demandas trazidas.",
             "palavras_alvo": (100, 200)},
            {"id": "procedimento", "label": "Procedimento",
             "hint": "Setting, número de sessões, técnicas/abordagem utilizadas, instrumentos aplicados.",
             "palavras_alvo": (100, 200)},
            {"id": "analise", "label": "Análise",
             "hint": "Discussão dos achados, sem diagnóstico nosológico, alinhada à abordagem.",
             "palavras_alvo": (200, 400)},
            {"id": "conclusao", "label": "Conclusão",
             "hint": "Síntese e resposta objetiva à demanda inicial.",
             "palavras_alvo": (80, 150)},
        ],
    },
    "laudo": {
        "titulo": "Laudo psicológico",
        "descricao": (
            "Documento formal com todos os blocos do relatório mais "
            "encaminhamentos e prazo de validade."
        ),
        "blocos": [
            {"id": "identificacao", "label": "Identificação",
             "hint": "Paciente ({{PACIENTE_NOME}}, {{PACIENTE_DOC}}, {{PACIENTE_NASC}}), solicitante, contexto avaliativo, período.",
             "palavras_alvo": (60, 140)},
            {"id": "descricao_demanda", "label": "Descrição da demanda",
             "hint": "Motivo do laudo, pergunta-guia, contexto legal/institucional.",
             "palavras_alvo": (120, 250)},
            {"id": "procedimento", "label": "Procedimento",
             "hint": "Setting, número de encontros, técnicas/abordagem, instrumentos.",
             "palavras_alvo": (120, 250)},
            {"id": "analise", "label": "Análise",
             "hint": "Discussão integrativa, articulando dados coletados; sem diagnóstico nosológico.",
             "palavras_alvo": (250, 500)},
            {"id": "conclusao", "label": "Conclusão",
             "hint": "Resposta objetiva à pergunta-guia. Explicitar limites.",
             "palavras_alvo": (100, 200)},
            {"id": "encaminhamentos", "label": "Encaminhamentos e prazo de validade",
             "hint": "Sugestões de seguimento; validade de 1 ano (padrão CFP), salvo indicação.",
             "palavras_alvo": (60, 120)},
        ],
    },
    "encaminhamento": {
        "titulo": "Documento de encaminhamento",
        "descricao": (
            "Solicita continuidade de atendimento por outro profissional/serviço."
        ),
        "blocos": [
            {"id": "motivo", "label": "Motivo do encaminhamento",
             "hint": "Por que a pessoa está sendo encaminhada.",
             "palavras_alvo": (30, 100)},
            {"id": "historico_resumido", "label": "Histórico resumido",
             "hint": "Panorama do acompanhamento até aqui (sessões, abordagem, instrumentos).",
             "palavras_alvo": (80, 200)},
            {"id": "solicitacao", "label": "Solicitação ao destinatário",
             "hint": "Ação esperada. Use {{DESTINATARIO}} se informado.",
             "palavras_alvo": (30, 100)},
        ],
    },
}

PLACEHOLDERS_PERMITIDOS = {
    "PACIENTE_NOME", "PACIENTE_DOC", "PACIENTE_NASC",
    "PROFISSIONAL_NOME", "PROFISSIONAL_CRP",
    "DATA_EMISSAO", "FINALIDADE", "DESTINATARIO",
}
