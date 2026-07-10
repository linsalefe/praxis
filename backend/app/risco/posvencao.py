"""Definição do protocolo de Posvenção — cuidado após uma morte por suicídio.

Fonte única da estrutura do formulário, servida ao frontend por
`GET /posvencao/definicao`, para o protocolo não ser duplicado/divergir na UI.

Enquadramento: posvenção é o conjunto de ações de cuidado prestadas APÓS um
suicídio, dirigidas aos enlutados (que têm risco aumentado), à comunicação
segura (prevenção de contágio) e à própria equipe. É registro de APOIO à decisão
clínica — não é diagnóstico, não substitui o julgamento do profissional, e o
sistema não faz alerta, notificação ou monitoramento automático.

Referências: WHO (2008) — Preventing suicide: how to start a survivors' group;
Diretrizes brasileiras de posvenção (ABEPS/CVV).
"""
from __future__ import annotations

from typing import Any

# --- Vínculo da pessoa falecida com o paciente-âncora ----------------------
VINCULOS_PERDA: list[dict[str, str]] = [
    {"valor": "proprio_paciente", "rotulo": "O próprio paciente (óbito por suicídio)"},
    {"valor": "familiar", "rotulo": "Familiar do paciente"},
    {"valor": "amigo", "rotulo": "Amigo(a)/pessoa próxima"},
    {"valor": "pessoa_rede", "rotulo": "Pessoa da rede/comunidade"},
    {"valor": "outro", "rotulo": "Outro"},
]
VINCULO_IDS = {v["valor"] for v in VINCULOS_PERDA}

# --- Andamento do processo de posvenção ------------------------------------
STATUS_POSVENCAO: list[dict[str, str]] = [
    {"valor": "aberto", "rotulo": "Aberto"},
    {"valor": "em_acompanhamento", "rotulo": "Em acompanhamento"},
    {"valor": "concluido", "rotulo": "Concluído"},
]
STATUS_IDS = {s["valor"] for s in STATUS_POSVENCAO}

# --- Passos do protocolo de posvenção --------------------------------------
# Preenchidos ao longo do acompanhamento. Conteúdo cifrado em repouso (PII de
# enlutados). Cada passo é um campo de texto que documenta o que foi feito.

POSVENCAO_PASSOS: list[dict[str, str]] = [
    {"id": "acolhimento", "titulo": "1. Acolhimento dos enlutados",
     "ajuda": "Escuta e acolhimento das pessoas enlutadas nas primeiras horas/dias após a perda."},
    {"id": "comunicacao_segura", "titulo": "2. Comunicação segura sobre a morte",
     "ajuda": "Informar de forma cuidadosa, sem detalhes de método nem romantização, prevenindo o contágio (efeito Werther)."},
    {"id": "avaliacao_enlutados", "titulo": "3. Avaliação de risco dos enlutados",
     "ajuda": "Enlutados por suicídio têm risco aumentado. Avaliar cada pessoa próxima (ver rastreio C-SSRS) e sinalizar quem precisa de cuidado."},
    {"id": "rede_apoio", "titulo": "4. Articulação da rede de apoio",
     "ajuda": "Mobilizar família, CAPS, UBS/APS e grupos de apoio a sobreviventes de suicídio."},
    {"id": "luto", "titulo": "5. Cuidado com o processo de luto",
     "ajuda": "Acompanhar o luto e encaminhar, quando indicado, a grupos de apoio a sobreviventes."},
    {"id": "cuidado_equipe", "titulo": "6. Cuidado com a equipe",
     "ajuda": "Debriefing e cuidado com os profissionais envolvidos — o luto e o impacto também os atingem."},
    {"id": "encaminhamentos", "titulo": "7. Encaminhamentos e seguimento",
     "ajuda": "Encaminhamentos realizados e plano de acompanhamento combinado."},
]
PASSOS_IDS = {p["id"] for p in POSVENCAO_PASSOS}


def definicao() -> dict[str, Any]:
    """Payload servido ao frontend (fonte única do formulário)."""
    return {
        "titulo": "Posvenção — cuidado após morte por suicídio",
        "fonte": (
            "Protocolo de posvenção (WHO, 2008; diretrizes brasileiras ABEPS/CVV). "
            "Registro de apoio à decisão clínica — não substitui a avaliação do "
            "profissional; o Práxis não faz alerta ou monitoramento automático."
        ),
        "vinculos_perda": VINCULOS_PERDA,
        "status": STATUS_POSVENCAO,
        "passos": POSVENCAO_PASSOS,
    }
