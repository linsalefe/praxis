"""Fatores de risco psicossocial da NR-1 — fonte única do checklist do laudo.

Categorias alinhadas às diretrizes de riscos psicossociais no trabalho (NR-1 /
GRO-PGR; referência ISO 45003). Servidas ao frontend por
`GET /laudos-nr1/definicao`. Cada fator é avaliado pelo profissional em um nível
(baixo/médio/alto ou não se aplica), com observação.

Apoio à elaboração do laudo — a responsabilidade técnica é do profissional.
"""
from __future__ import annotations

from typing import Any

NIVEIS = ("na", "baixo", "medio", "alto")

FATORES_NR1: list[dict[str, str]] = [
    {"id": "carga_ritmo", "titulo": "Carga e ritmo de trabalho",
     "descricao": "Volume, intensidade e pressão de tempo; metas e prazos."},
    {"id": "jornada", "titulo": "Jornada e tempo de trabalho",
     "descricao": "Duração, horas extras, trabalho noturno, previsibilidade da escala."},
    {"id": "autonomia_controle", "titulo": "Autonomia e controle",
     "descricao": "Grau de influência da pessoa sobre como e quando realiza o trabalho."},
    {"id": "clareza_papeis", "titulo": "Clareza de papéis e demandas",
     "descricao": "Definição de funções, expectativas e prioridades; conflito de papéis."},
    {"id": "relacoes_apoio", "titulo": "Relações socioprofissionais e apoio",
     "descricao": "Qualidade das relações, apoio de liderança e colegas."},
    {"id": "reconhecimento", "titulo": "Reconhecimento e recompensa",
     "descricao": "Equilíbrio entre esforço e reconhecimento; justiça organizacional."},
    {"id": "assedio_violencia", "titulo": "Assédio e violência",
     "descricao": "Assédio moral/sexual, discriminação e violência (interna ou de terceiros)."},
    {"id": "exigencia_emocional", "titulo": "Exigência emocional",
     "descricao": "Contato com sofrimento, público difícil, necessidade de controlar emoções."},
    {"id": "inseguranca", "titulo": "Insegurança no trabalho",
     "descricao": "Estabilidade do vínculo, medo de perda do emprego, mudanças mal comunicadas."},
    {"id": "conciliacao_vida", "titulo": "Conciliação trabalho–vida",
     "descricao": "Interferência do trabalho na vida pessoal; disponibilidade fora do horário."},
    {"id": "gestao_mudancas", "titulo": "Gestão de mudanças e comunicação",
     "descricao": "Participação, transparência e apoio em processos de mudança."},
]

FATOR_IDS = {f["id"] for f in FATORES_NR1}


def definicao() -> dict[str, Any]:
    return {
        "fatores": FATORES_NR1,
        "niveis": [
            {"valor": "na", "rotulo": "Não se aplica"},
            {"valor": "baixo", "rotulo": "Baixo"},
            {"valor": "medio", "rotulo": "Médio"},
            {"valor": "alto", "rotulo": "Alto"},
        ],
    }
