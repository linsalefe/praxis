"""Definição do rastreio C-SSRS (Columbia Suicide Severity Rating Scale) e do
Plano de Segurança (Stanley-Brown).

Fonte única da estrutura do formulário — servida ao frontend por
`GET /risco/definicao`, para o instrumento não ser duplicado/divergir na UI.

Enquadramento (importante): este é um rastreio de APOIO à decisão clínica. Não é
diagnóstico nem triagem automática que substitui o julgamento do profissional. O
sistema não faz alerta, notificação ou monitoramento automático de risco.
"""
from __future__ import annotations

from typing import Any

# --- Rastreio C-SSRS (versão screener, 6 itens sim/não) --------------------
# Itens 1-2: ideação. 3-5: ideação com método/intenção/plano (gravidade
# crescente). 6: comportamento suicida (ao longo da vida e recente).

CSSRS_ITENS: list[dict[str, Any]] = [
    {"id": "q1", "grupo": "ideacao",
     "texto": "Desejou estar morto(a) ou poder dormir e não acordar?"},
    {"id": "q2", "grupo": "ideacao",
     "texto": "Teve, de fato, pensamentos de se matar/tirar a própria vida?"},
    {"id": "q3", "grupo": "ideacao",
     "texto": "Pensou em COMO faria isso (algum método), sem intenção de agir?"},
    {"id": "q4", "grupo": "ideacao",
     "texto": "Teve algum grau de intenção de agir sobre esses pensamentos?"},
    {"id": "q5", "grupo": "ideacao",
     "texto": "Começou a elaborar ou já elaborou os detalhes de um plano, com intenção de executá-lo?"},
    {"id": "q6", "grupo": "comportamento",
     "texto": "Alguma vez fez algo, começou a fazer ou se preparou para acabar com a própria vida?"},
]

# Sub-pergunta do item de comportamento (q6): quando ocorreu.
COMPORTAMENTO_QUANDO = [
    {"valor": "nao", "rotulo": "Nunca"},
    {"valor": "vida", "rotulo": "Ao longo da vida (há mais de 3 meses)"},
    {"valor": "recente", "rotulo": "Nos últimos 3 meses"},
]

# --- Plano de Segurança (Stanley & Brown, 2012) ----------------------------
# Passos preenchidos COM o paciente. Conteúdo cifrado em repouso (PII de rede).

PLANO_SEGURANCA_PASSOS: list[dict[str, str]] = [
    {"id": "sinais_alerta", "titulo": "1. Sinais de alerta",
     "ajuda": "Pensamentos, imagens, humor, situações ou comportamentos que indicam que uma crise pode estar se aproximando."},
    {"id": "estrategias_internas", "titulo": "2. Estratégias de enfrentamento internas",
     "ajuda": "Coisas que a pessoa pode fazer sozinha para se distrair, sem contatar outra pessoa."},
    {"id": "contatos_distracao", "titulo": "3. Pessoas e locais que ajudam a distrair",
     "ajuda": "Pessoas e ambientes sociais que ajudam a afastar a crise (sem necessariamente falar do risco)."},
    {"id": "contatos_ajuda", "titulo": "4. Pessoas a quem pedir ajuda",
     "ajuda": "Familiares ou amigos a quem a pessoa pode recorrer e pedir ajuda em crise."},
    {"id": "profissionais_agencias", "titulo": "5. Profissionais e serviços de emergência",
     "ajuda": "Profissionais/serviços e contatos de emergência. Ex.: CVV 188, CAPS de referência, SAMU 192, emergência psiquiátrica."},
    {"id": "ambiente_seguro", "titulo": "6. Tornar o ambiente seguro",
     "ajuda": "Reduzir o acesso a meios (medicamentos, armas, etc.). Com quem os meios podem ficar guardados."},
    {"id": "motivos_para_viver", "titulo": "Motivos para viver",
     "ajuda": "Razões que tornam a vida importante e valem a pena serem lembradas na crise."},
]

PLANO_SEGURANCA_IDS = {p["id"] for p in PLANO_SEGURANCA_PASSOS}


def definicao() -> dict[str, Any]:
    """Payload servido ao frontend (fonte única do formulário)."""
    return {
        "cssrs": {
            "titulo": "C-SSRS — Rastreio de risco de suicídio (Columbia)",
            "fonte": (
                "Columbia-Suicide Severity Rating Scale (Posner et al., 2011). "
                "Versão de rastreio. Instrumento de apoio à decisão clínica — não "
                "substitui a avaliação do profissional."
            ),
            "itens": CSSRS_ITENS,
            "comportamento_quando": COMPORTAMENTO_QUANDO,
        },
        "plano_seguranca": {
            "titulo": "Plano de Segurança (Stanley-Brown)",
            "passos": PLANO_SEGURANCA_PASSOS,
        },
        "niveis": [
            {"valor": "minimo", "rotulo": "Mínimo"},
            {"valor": "baixo", "rotulo": "Baixo"},
            {"valor": "moderado", "rotulo": "Moderado"},
            {"valor": "alto", "rotulo": "Alto"},
        ],
    }
