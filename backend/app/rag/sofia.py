"""Prompt e chamada ao LLM (GPT-5.1-mini) com guardrails clínicos."""
from __future__ import annotations

from dataclasses import dataclass

from openai import AsyncOpenAI

from app.config import get_settings
from app.rag.retriever import Hit

SISTEMA = """Você é a Sofia, assistente clínica do Práxis (CENAT), voltada a psicólogos
que trabalham com novas abordagens em saúde mental (Diálogo Aberto, Ouvir Vozes,
GAM, PTMF, WRAP, Redução de Danos).

Diretrizes obrigatórias:

1. Baseie-se **prioritariamente nos trechos do acervo do CENAT** fornecidos abaixo.
   Se os trechos não sustentarem a resposta, diga isso com clareza e responda
   apenas com conhecimento clínico geral seguro — sem inventar citações.
2. **Cite as fontes** ao final da resposta na seção "Fontes:", usando o formato
   `[T{n}] Título — Autor · cap. X · pp. Y-Z`.
3. Para trechos marcados como **[TERCEIRO]** (obras que não são da editora CENAT),
   **NUNCA transcreva o texto literalmente**. Parafraseie a ideia com suas
   palavras e cite normalmente. Não copie frases inteiras dos trechos.
4. Tom: técnico-clínico, respeitoso, sem prometer resultados. Evite diagnósticos
   assertivos ou prescrição medicamentosa.
5. Encerre com o disclaimer: *"Esta resposta é apoio ao raciocínio clínico; a
   responsabilidade técnica pela conduta é do profissional (Manual CFP 2025)."*
6. Escreva em **português do Brasil**, direto ao ponto (200-500 palavras).
"""


@dataclass
class Resposta:
    resposta: str
    sem_respaldo: bool
    modelo: str


def _formatar_contexto(hits: list[Hit]) -> str:
    partes: list[str] = []
    for i, h in enumerate(hits, start=1):
        tag = "[TERCEIRO] " if h.is_terceiro else ""
        cap = f"cap. {h.capitulo}" if h.capitulo else "cap. n/d"
        pg = (
            f"pp. {h.pagina_inicio}-{h.pagina_fim}"
            if h.pagina_inicio and h.pagina_fim and h.pagina_inicio != h.pagina_fim
            else f"p. {h.pagina_inicio}" if h.pagina_inicio else "p. n/d"
        )
        cabecalho = f"[T{i}] {tag}{h.titulo} — {h.autor} · {cap} · {pg} · sim={h.similaridade:.2f}"
        partes.append(f"{cabecalho}\n{h.texto}")
    return "\n\n---\n\n".join(partes)


async def responder(pergunta: str, hits: list[Hit], sobre_paciente: bool = False) -> Resposta:
    s = get_settings()
    sem_respaldo = not hits or max((h.similaridade for h in hits), default=0.0) < s.rag_sim_min

    aviso_paciente = ""
    if sobre_paciente:
        aviso_paciente = (
            "\n\nO psicólogo indicou que a pergunta é sobre um caso específico. "
            "Por política de privacidade (LGPD), NÃO recebemos dados do paciente. "
            "Responda de forma genérica e sugira como aplicar clinicamente."
        )

    contexto = _formatar_contexto(hits) if hits else "(nenhum trecho relevante encontrado no acervo)"
    if sem_respaldo:
        contexto += (
            "\n\n(Atenção: nenhum trecho com similaridade suficiente. "
            "Você deve avisar o usuário que o acervo não sustenta esta resposta.)"
        )

    client = AsyncOpenAI(api_key=s.openai_api_key)
    completion = await client.chat.completions.create(
        model=s.llm_model,
        messages=[
            {"role": "system", "content": SISTEMA + aviso_paciente},
            {
                "role": "user",
                "content": (
                    f"Pergunta do profissional:\n{pergunta}\n\n"
                    f"Trechos do acervo (referências T1..Tk):\n\n{contexto}"
                ),
            },
        ],
        temperature=0.2,
    )
    return Resposta(
        resposta=(completion.choices[0].message.content or "").strip(),
        sem_respaldo=sem_respaldo,
        modelo=s.llm_model,
    )
