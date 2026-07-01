"""Analisador de supervisão: LLM compara N abordagens com base no acervo.

Reusa RAG (Sprint 2) + contexto anonimizado do paciente (Sprint 5).
Modo avulso: recebe texto livre do profissional, não persistido.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.preparacao.contexto import ContextoAnonimo
from app.rag.embeddings import embed_query
from app.rag.retriever import Hit, buscar

PROMPT_VERSAO = "supv-v1"

ABORDAGEM_LABEL = {
    "dialogo_aberto": "Diálogo Aberto",
    "ouvir_vozes": "Ouvir Vozes",
    "gam": "Gestão Autônoma da Medicação (GAM)",
    "ptmf": "Power Threat Meaning Framework (PTMF)",
    "wrap": "Wellness Recovery Action Plan (WRAP)",
    "reducao_danos": "Redução de Danos",
}

# Abordagens comparadas por default (as 4 que o acervo cobre com maior densidade).
ABORDAGENS_PADRAO = ["dialogo_aberto", "ouvir_vozes", "gam", "ptmf"]


SISTEMA = """Você é o assistente de **Supervisão / Estudo de Caso** do Práxis
(CENAT), voltado à **formação continuada** de psicólogos que trabalham
com novas abordagens em saúde mental.

Seu trabalho não é dar conduta. É ajudar o profissional a **pensar o caso
por múltiplas lentes**, comparando como diferentes abordagens o
enquadrariam, com apoio direto no acervo do CENAT.

Diretrizes obrigatórias:

1. **Isto é apoio formativo, não conduta clínica.** A responsabilidade
   técnica da conduta é sempre do profissional.
2. Baseie-se APENAS no que está no caso descrito e nos trechos do acervo
   (marcados como [Tn]). Se falta dado para uma leitura, diga.
3. Para cada abordagem comparada, produza:
   - **Leitura**: como ela enquadra este caso especificamente
   - **Movimentos possíveis** dentro dessa abordagem
   - **Prós e limites** desta leitura para este caso
   - **Base no acervo**: cite chunks pertinentes [Tn]
4. Chunks marcados como **[TERCEIRO]** exigem paráfrase — NUNCA cite
   literalmente. Traga a ideia com suas palavras.
5. Não invente nome ou dados. Se o retrato do caso for anonimizado, use
   "o caso" / "a pessoa" / "o paciente".
6. Não sugira diagnóstico nosológico nem prescrição.
7. Escreva em português do Brasil, tom técnico-clínico, respeitoso.

Estrutura da saída em Markdown, com estes cabeçalhos exatos:

## Síntese do caso
## Leituras por abordagem
### {rótulo da abordagem 1}
- **Leitura**: …
- **Movimentos possíveis**: …
- **Prós**: …
- **Limites**: …
- **Base no acervo**: …
### {rótulo da abordagem 2}
…
## Hipóteses e temas em aberto
## Caminhos formativos sugeridos
## Atenções éticas
## Fontes

Encerre com:
*Este material é apoio formativo. A responsabilidade técnica pela conduta
clínica é do profissional (Manual CFP 2025).*
"""


@dataclass
class Analise:
    texto: str
    provider_id: str
    hits: list[Hit] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)


def _query_para_acervo(descricao_caso: str, abordagens: list[str]) -> str:
    rotulos = " ".join(ABORDAGEM_LABEL.get(a, a) for a in abordagens)
    return f"{rotulos}\n{descricao_caso[:1200]}"


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
        linhas.append(
            f"[T{i}] {tag}{h.titulo} — {h.autor} · {cap} · {pg} · sim={h.similaridade:.2f}\n{h.texto}"
        )
    return "\n\n---\n\n".join(linhas)


def _abordagens_para_este_caso(ctx: ContextoAnonimo | None, abordagem_prof: str | None) -> list[str]:
    """Mantém as 4 padrão + a preferida do profissional se estiver fora delas.

    Se contexto de paciente indicar histórico com WRAP/RD, agrega essas também.
    """
    abordagens = list(ABORDAGENS_PADRAO)
    if abordagem_prof and abordagem_prof in ABORDAGEM_LABEL and abordagem_prof not in abordagens:
        abordagens.append(abordagem_prof)
    # Se o retrato do paciente cita explicitamente WRAP/RD, adiciona.
    if ctx is not None:
        blob = (ctx.to_prompt_string() or "").lower()
        if "wrap" in blob and "wrap" not in abordagens:
            abordagens.append("wrap")
        if ("redução de danos" in blob or "reducao_danos" in blob) and "reducao_danos" not in abordagens:
            abordagens.append("reducao_danos")
    return abordagens


async def analisar(
    session: AsyncSession,
    *,
    descricao_caso: str,
    ctx_paciente: ContextoAnonimo | None,
    abordagem_prof: str | None,
) -> Analise:
    s = get_settings()
    abordagens = _abordagens_para_este_caso(ctx_paciente, abordagem_prof)

    # 1) RAG
    q_emb = await embed_query(_query_para_acervo(descricao_caso, abordagens))
    hits = await buscar(session, q_emb, top_k=8)

    # 2) prompt
    rotulos_txt = "\n".join(f"- {ABORDAGEM_LABEL[a]}" for a in abordagens)
    ctx_txt = f"\n\n### Retrato clínico anonimizado do paciente:\n{ctx_paciente.to_prompt_string()}" if ctx_paciente else ""
    contexto_acervo = _formatar_hits(hits)

    prompt_usuario = (
        f"### Caso apresentado\n{descricao_caso}"
        f"{ctx_txt}\n\n"
        f"### Abordagens a comparar (nesta ordem)\n{rotulos_txt}\n\n"
        f"### Trechos do acervo (referências T1..Tk)\n{contexto_acervo}\n\n"
        "Produza a análise em Markdown, ~700-1300 palavras, seguindo a "
        "estrutura da instrução do sistema. Uma sub-seção `###` para cada "
        "abordagem, na ordem listada acima."
    )

    client = AsyncOpenAI(api_key=s.openai_api_key)
    completion = await client.chat.completions.create(
        model=s.llm_model,
        temperature=0.25,
        messages=[
            {"role": "system", "content": SISTEMA},
            {"role": "user", "content": prompt_usuario},
        ],
    )
    texto = (completion.choices[0].message.content or "").strip()

    return Analise(
        texto=texto,
        provider_id=f"openai:{s.llm_model}",
        hits=hits,
        meta={
            "abordagens_comparadas": abordagens,
            "n_chunks_acervo": len(hits),
            "prompt_versao": PROMPT_VERSAO,
        },
    )
