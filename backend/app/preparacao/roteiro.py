"""LLM que produz o roteiro pré-sessão a partir do contexto anonimizado + acervo."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.preparacao.contexto import ContextoAnonimo
from app.rag.embeddings import embed_query
from app.rag.retriever import Hit, buscar

ABORDAGEM_LABEL = {
    "dialogo_aberto": "Diálogo Aberto",
    "ouvir_vozes": "Ouvir Vozes",
    "gam": "Gestão Autônoma da Medicação (GAM)",
    "ptmf": "Power Threat Meaning Framework (PTMF)",
    "wrap": "Wellness Recovery Action Plan (WRAP)",
    "reducao_danos": "Redução de Danos",
    "outros": "abordagem própria",
}


SISTEMA = """Você é o assistente de **Preparação de Sessão** do Práxis (CENAT). Antes
de um atendimento, você recebe um **retrato clínico anonimizado** do paciente
(sem nome, contato ou documento) e trechos do acervo do CENAT. Sua tarefa é
produzir um **roteiro pré-sessão** que apoie o profissional a chegar mais
presente ao encontro.

Diretrizes obrigatórias:

1. **NÃO** invente nome do paciente, familiares ou terceiros. Refira-se
   sempre como "o paciente" / "a pessoa" / "quem está sendo atendido".
2. Sugestões são **apoio** — a decisão clínica é do profissional. Evite
   linguagem prescritiva ("você deve"); prefira "poderia" / "talvez valha".
3. Use os trechos [Tn] do acervo para embasar sugestões. Se um trecho é
   [TERCEIRO], PARAFRASEIE — nunca cite literal.
4. Adapte a linguagem à abordagem do profissional indicada abaixo.
5. Se o histórico é insuficiente para uma seção, escreva "Sem histórico
   suficiente para essa leitura" — não invente.

Estruture a saída **em Markdown** com estes cabeçalhos exatos:

## Contexto rápido
## Pontos a retomar
## Hipóteses e temas para escutar
## Movimentos sugeridos (linguagem da abordagem)
## Perguntas úteis do acervo
## Atenções éticas

Ao final adicione:

*Este roteiro é apoio ao raciocínio clínico; a responsabilidade técnica
pela conduta é do profissional (Manual CFP 2025).*
"""


@dataclass
class Roteiro:
    texto: str
    provider_id: str
    hits: list[Hit] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)


def _query_para_acervo(ctx: ContextoAnonimo, abordagem_rot: str | None) -> str:
    """Concatena sinais do contexto em uma query densa para o retriever."""
    partes: list[str] = []
    if abordagem_rot:
        partes.append(f"abordagem {abordagem_rot}")
    # pega os primeiros N caracteres das evoluções + instrumentos
    for e in ctx.evolucoes_texto[:2]:
        partes.append(e[:400])
    for i in ctx.instrumentos_texto[:1]:
        partes.append(i[:400])
    if not partes:
        partes.append("preparação de sessão psicoterápica; hipóteses clínicas")
    return "\n".join(partes)


def _formatar_hits(hits: list[Hit]) -> str:
    if not hits:
        return "(nenhum trecho relevante do acervo encontrado)"
    linhas: list[str] = []
    for i, h in enumerate(hits, start=1):
        tag = "[TERCEIRO] " if h.is_terceiro else ""
        cap = f"cap. {h.capitulo}" if h.capitulo else "cap. n/d"
        pg = (
            f"pp. {h.pagina_inicio}-{h.pagina_fim}"
            if h.pagina_inicio and h.pagina_fim and h.pagina_inicio != h.pagina_fim
            else f"p. {h.pagina_inicio}" if h.pagina_inicio else "p. n/d"
        )
        linhas.append(f"[T{i}] {tag}{h.titulo} — {h.autor} · {cap} · {pg} · sim={h.similaridade:.2f}\n{h.texto}")
    return "\n\n---\n\n".join(linhas)


async def preparar_roteiro(
    session: AsyncSession,
    ctx: ContextoAnonimo,
    abordagem_prof: str | None,
) -> Roteiro:
    s = get_settings()
    ab_rot = ABORDAGEM_LABEL.get(abordagem_prof or "", abordagem_prof) if abordagem_prof else None

    # 1) buscar no acervo
    q = _query_para_acervo(ctx, ab_rot)
    q_emb = await embed_query(q)
    hits = await buscar(session, q_emb, top_k=6)

    # 2) montar mensagem para o LLM
    ctx_txt = ctx.to_prompt_string()
    contexto_acervo = _formatar_hits(hits)

    tom = ""
    if ab_rot:
        tom = f"\n\nAbordagem do profissional: **{ab_rot}**. Adapte tom, terminologia e sugestões a ela."

    client = AsyncOpenAI(api_key=s.openai_api_key)
    completion = await client.chat.completions.create(
        model=s.llm_model,
        temperature=0.25,
        messages=[
            {"role": "system", "content": SISTEMA + tom},
            {"role": "user", "content":
                f"{ctx_txt}\n\n## Trechos do acervo (referências T1..Tk)\n{contexto_acervo}\n\n"
                "Produza agora o roteiro pré-sessão em Markdown, ~400-700 palavras."},
        ],
    )
    texto = (completion.choices[0].message.content or "").strip()

    return Roteiro(
        texto=texto,
        provider_id=f"openai:{s.llm_model}",
        hits=hits,
        meta={
            "n_evolucoes_usadas": len(ctx.evolucoes_texto),
            "n_instrumentos_usados": len(ctx.instrumentos_texto),
            "n_chunks_acervo": len(hits),
            "abordagem": abordagem_prof,
        },
    )
