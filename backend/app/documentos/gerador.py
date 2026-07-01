"""LLM (gpt-5.4-mini) que produz o rascunho estruturado do documento.

Estratégia de privacidade: **placeholders + anonimização**.
- O LLM recebe o retrato clínico anonimizado do paciente (Sprint 5).
- É instruído a usar placeholders {{PACIENTE_NOME}} etc. em vez de nomes.
- O server substitui os placeholders localmente antes de persistir.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from openai import AsyncOpenAI

from app.config import get_settings
from app.documentos.templates import TEMPLATES
from app.preparacao.contexto import ContextoAnonimo

PROMPT_VERSAO = "doc-cfp-v1"


SISTEMA = """Você é o assistente de **documentos escritos** do Práxis (CENAT),
que redige rascunhos dos cinco tipos de documento da Resolução CFP 06/2019:
declaração, atestado psicológico, relatório, laudo e encaminhamento.

Diretrizes obrigatórias:

1. **NUNCA escreva o nome do paciente**. Sempre use os placeholders
   `{{PACIENTE_NOME}}`, `{{PACIENTE_DOC}}` (documento), `{{PACIENTE_NASC}}`
   (nascimento). O servidor vai substituí-los localmente.
2. Use também `{{PROFISSIONAL_NOME}}`, `{{PROFISSIONAL_CRP}}`,
   `{{DATA_EMISSAO}}`, `{{FINALIDADE}}` e (se aplicável) `{{DESTINATARIO}}`.
3. **NUNCA cite CID** ou diagnóstico nosológico — psicólogos não podem
   emitir CID (atribuição médica).
4. Não afirme fatos que não estejam no retrato clínico anonimizado; se
   um bloco não tem base, escreva "Sem informação suficiente no
   histórico até a data desta emissão" nesse bloco.
5. Adapte o tom à abordagem do profissional (se informada).
6. Escreva em português do Brasil, tom técnico-clínico, respeitoso.
7. Retorne **exclusivamente JSON válido** com uma chave por bloco
   solicitado (id do bloco). Cada valor é uma string.
"""


@dataclass
class RascunhoGerado:
    conteudo: dict[str, str]  # bloco_id -> texto (com placeholders)
    provider_id: str
    prompt_versao: str


def _formatar_blocos(tipo: str) -> str:
    template = TEMPLATES[tipo]
    linhas = [f"Tipo: **{template['titulo']}** — {template['descricao']}",
              "",
              "Blocos obrigatórios (chaves do JSON de retorno):"]
    for b in template["blocos"]:
        pmin, pmax = b["palavras_alvo"]
        linhas.append(f"- `{b['id']}` ({b['label']}, ~{pmin}-{pmax} palavras): {b['hint']}")
    return "\n".join(linhas)


async def gerar_documento(
    tipo: str,
    finalidade: str,
    destinatario: str | None,
    ctx: ContextoAnonimo,
    abordagem_prof: str | None,
) -> RascunhoGerado:
    if tipo not in TEMPLATES:
        raise ValueError(f"tipo desconhecido: {tipo}")
    s = get_settings()
    template = TEMPLATES[tipo]
    blocos_txt = _formatar_blocos(tipo)

    tom = ""
    if abordagem_prof:
        tom = f"\n\nAbordagem do profissional: **{abordagem_prof}**. Adapte o tom."

    dest_txt = f"\nDestinatário do documento: {destinatario}" if destinatario else ""

    ctx_txt = ctx.to_prompt_string()

    prompt_usuario = (
        f"{blocos_txt}\n\n"
        f"Finalidade do documento: {finalidade}"
        f"{dest_txt}\n\n"
        f"Retrato clínico anonimizado:\n{ctx_txt}\n\n"
        "Devolva agora o JSON com uma chave por bloco listado acima. "
        "Use placeholders em todo lugar que exija dados do paciente ou do "
        "profissional; NÃO invente nomes."
    )

    client = AsyncOpenAI(api_key=s.openai_api_key)
    completion = await client.chat.completions.create(
        model=s.llm_model,
        response_format={"type": "json_object"},
        temperature=0.15,
        messages=[
            {"role": "system", "content": SISTEMA + tom},
            {"role": "user", "content": prompt_usuario},
        ],
    )
    raw = (completion.choices[0].message.content or "{}").strip()
    try:
        data: dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError:
        i, j = raw.find("{"), raw.rfind("}")
        data = json.loads(raw[i : j + 1]) if i != -1 and j != -1 else {}

    conteudo: dict[str, str] = {}
    for b in template["blocos"]:
        v = data.get(b["id"])
        conteudo[b["id"]] = v.strip() if isinstance(v, str) else "Sem informação suficiente no histórico até a data desta emissão."

    return RascunhoGerado(
        conteudo=conteudo,
        provider_id=f"openai:{s.llm_model}",
        prompt_versao=PROMPT_VERSAO,
    )
