"""LLM que transforma transcrição/resumo em Evolucao CFP (JSON estruturado)."""
from __future__ import annotations

import json
from dataclasses import dataclass

from openai import AsyncOpenAI

from app.config import get_settings

PROMPT_VERSAO = "cfp-v1"

_ABORDAGEM_LABEL = {
    "dialogo_aberto": "Diálogo Aberto",
    "ouvir_vozes": "Ouvir Vozes",
    "gam": "Gestão Autônoma da Medicação (GAM)",
    "ptmf": "Power Threat Meaning Framework (PTMF)",
    "wrap": "Wellness Recovery Action Plan (WRAP)",
    "reducao_danos": "Redução de Danos",
    "outros": "abordagem própria",
}

# Diretriz específica de Diálogo Aberto (práticas dialógicas): estrutura a
# evolução pelos princípios dialógicos, mantendo os 4 campos CFP.
_DIRETRIZ_DIALOGO_ABERTO = """

O profissional trabalha com **Diálogo Aberto** (práticas dialógicas). Sem inventar
dados, estruture a evolução segundo os princípios dialógicos:
- identificacao: registre quem participou do encontro além da pessoa atendida
  (familiares, rede social, outros profissionais) — o cuidado se faz na rede.
- demanda_objetivos: apresente a demanda como formulada pelas diferentes vozes
  presentes (polifonia), preservando divergências, sem reduzir a uma única versão.
- evolucao: registre o diálogo — falas significativas que foram respondidas
  (responsividade), a tolerância à incerteza (sem conclusões precipitadas) e os
  múltiplos pontos de vista. Evite a voz de perito unilateral.
- encaminhamento: registre as decisões tomadas de forma compartilhada com a pessoa
  e sua rede (transparência) e o próximo encontro combinado.
Mantenha português técnico-clínico, 3ª pessoa; não sugira diagnóstico nem prescrição."""


def montar_diretriz(abordagem_prof: str | None) -> str:
    """Diretriz de abordagem injetada no system prompt (puro, testável).

    Diálogo Aberto recebe um template dialógico completo; as demais abordagens
    recebem apenas uma frase de tom (comportamento anterior preservado).
    """
    if not abordagem_prof:
        return ""
    if abordagem_prof == "dialogo_aberto":
        return _DIRETRIZ_DIALOGO_ABERTO
    rotulo = _ABORDAGEM_LABEL.get(abordagem_prof, abordagem_prof)
    return f"\n\nO profissional trabalha com **{rotulo}** — mantenha a linguagem coerente com essa abordagem."


SISTEMA = """Você é o **Scribe** do Práxis (CENAT), um assistente que transforma a nota
clínica bruta de uma sessão de psicoterapia em uma **evolução clínica estruturada**
segundo os campos usados pelo Conselho Federal de Psicologia (CFP):

  1. identificacao — quem é o paciente, data/contexto do atendimento, referência à sessão.
  2. demanda_objetivos — avaliação da demanda apresentada e objetivos terapêuticos.
  3. evolucao — descrição da sessão, hipóteses, movimento clínico, técnicas.
  4. encaminhamento — condutas, próximos passos, encaminhamentos ou encerramento.

Diretrizes obrigatórias:

- Escreva em português do Brasil, em tom técnico-clínico, na 3ª pessoa.
- **Não invente informações** que não estejam na entrada. Se um campo não tem base,
  escreva "Sem informação registrada na sessão" nesse campo.
- Não sugira diagnóstico nosológico nem prescrição medicamentosa.
- Preserve nomes próprios como estão na entrada.
- Retorne **exclusivamente JSON válido** com estas quatro chaves e apenas elas,
  cada valor sendo uma string (pode ter parágrafos separados por \\n\\n).
"""


@dataclass
class Estruturada:
    identificacao: str
    demanda_objetivos: str
    evolucao: str
    encaminhamento: str
    provider_id: str
    prompt_versao: str


async def estruturar(entrada: str, abordagem_prof: str | None) -> Estruturada:
    """Chama o LLM e devolve os 4 blocos CFP.

    entrada: transcrição do áudio ou resumo digitado pelo profissional.
    abordagem_prof: enum de User.abordagem — injeta tom no system prompt.
    """
    s = get_settings()
    tom = montar_diretriz(abordagem_prof)

    client = AsyncOpenAI(api_key=s.openai_api_key)
    completion = await client.chat.completions.create(
        model=s.llm_model,
        response_format={"type": "json_object"},
        temperature=0.15,
        messages=[
            {"role": "system", "content": SISTEMA + tom},
            {
                "role": "user",
                "content": (
                    "Nota clínica bruta (transcrição ou resumo):\n\n"
                    f"---\n{entrada}\n---\n\n"
                    "Devolva agora o JSON com identificacao, demanda_objetivos, "
                    "evolucao, encaminhamento."
                ),
            },
        ],
    )
    raw = (completion.choices[0].message.content or "{}").strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # tentativa de recuperar bloco entre chaves
        i, j = raw.find("{"), raw.rfind("}")
        data = json.loads(raw[i : j + 1]) if i != -1 and j != -1 else {}

    def _get(k: str) -> str:
        v = data.get(k)
        if isinstance(v, str):
            return v.strip()
        return "Sem informação registrada na sessão."

    return Estruturada(
        identificacao=_get("identificacao"),
        demanda_objetivos=_get("demanda_objetivos"),
        evolucao=_get("evolucao"),
        encaminhamento=_get("encaminhamento"),
        provider_id=f"openai:{s.llm_model}",
        prompt_versao=PROMPT_VERSAO,
    )
