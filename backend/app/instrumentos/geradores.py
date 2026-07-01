"""Geradores de saída dos instrumentos: formulador Maastricht + planejador WRAP.

Usam `gpt-5.4-mini` via OpenAI. O formulador Maastricht faz RAG opcional no
acervo (Sprint 2) para embasar a discussão clínica com paráfrase de terceiros.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.rag.embeddings import embed_query
from app.rag.retriever import Hit, buscar

PROMPT_VERSAO = "instr-v1"


@dataclass
class SaidaGerada:
    texto: str
    provider_id: str
    hits: list[Hit]


def _flatten_respostas(definicao: dict[str, Any], respostas: dict[str, Any]) -> str:
    """Concatena perguntas+respostas em texto legível para o LLM."""
    linhas: list[str] = []
    for sec in definicao.get("secoes", []):
        sec_id = sec["id"]
        resp_sec: dict[str, Any] = respostas.get(sec_id, {}) or {}
        linhas.append(f"\n## {sec['titulo']}")
        for p in sec.get("perguntas", []):
            v = resp_sec.get(p["id"])
            if v in (None, "", []):
                linhas.append(f"- **{p['label']}**: _(não respondido)_")
            elif isinstance(v, list):
                linhas.append(f"- **{p['label']}**: {', '.join(map(str, v))}")
            elif isinstance(v, bool):
                linhas.append(f"- **{p['label']}**: {'sim' if v else 'não'}")
            else:
                linhas.append(f"- **{p['label']}**: {v}")
    return "\n".join(linhas).strip()


# --------------------------------------------------------------------------
# Maastricht → formulação clínica
# --------------------------------------------------------------------------

SISTEMA_MAASTRICHT = """Você é o assistente clínico do Práxis (CENAT), coescrevendo uma
**formulação Maastricht** a partir das respostas de uma entrevista estruturada
sobre a experiência de ouvir vozes.

Diretrizes obrigatórias:

1. NÃO é um diagnóstico. Você produz uma FORMULAÇÃO clínica — hipóteses
   integrativas sobre significado, função, gatilhos e recursos da pessoa.
2. Baseie-se apenas nas respostas fornecidas. Se uma seção não tem dado,
   diga isso explicitamente e sinalize como lacuna a investigar.
3. Use os trechos do acervo (marcados como [Tn]) para embasar a discussão;
   PARAFRASEIE trechos marcados como [TERCEIRO] — nunca copie o texto literal.
4. Tom técnico-clínico, respeitoso, coerente com a abordagem Ouvir Vozes:
   voz como experiência significativa (não sintoma a suprimir).
5. Estruture a saída em Markdown com estes cabeçalhos:
   ## Síntese da experiência
   ## Formulação — função e significado das vozes
   ## Gatilhos e mantenedores
   ## Recursos e estratégias já em uso
   ## Lacunas / próximas perguntas clínicas
   ## Direções terapêuticas sugeridas (sempre como sugestões, não prescrição)
   ## Fontes
6. Feche com o disclaimer:
   *"Este documento é apoio ao raciocínio clínico; a responsabilidade
   técnica pela conduta é do profissional (Manual CFP 2025)."*
"""


async def formular_maastricht(
    session: AsyncSession,
    definicao: dict[str, Any],
    respostas: dict[str, Any],
    abordagem_prof: str | None,
) -> SaidaGerada:
    s = get_settings()

    corpo = _flatten_respostas(definicao, respostas)

    # RAG: buscamos chunks relevantes usando o próprio corpo como query.
    hits: list[Hit] = []
    if corpo.strip():
        q_emb = await embed_query(f"formulação de ouvir vozes: {corpo[:600]}")
        hits = await buscar(session, q_emb, top_k=6)

    contexto = ""
    if hits:
        blocos = []
        for i, h in enumerate(hits, start=1):
            tag = "[TERCEIRO] " if h.is_terceiro else ""
            cap = f"cap. {h.capitulo}" if h.capitulo else "cap. n/d"
            pg = (f"pp. {h.pagina_inicio}-{h.pagina_fim}"
                  if h.pagina_inicio and h.pagina_fim else "p. n/d")
            blocos.append(f"[T{i}] {tag}{h.titulo} — {h.autor} · {cap} · {pg}\n{h.texto}")
        contexto = "\n\n---\n\n".join(blocos)
    else:
        contexto = "(nenhum trecho relevante do acervo)"

    tom = ""
    if abordagem_prof:
        tom = f"\n\nO profissional trabalha com **{abordagem_prof}** — mantenha coerência de linguagem."

    client = AsyncOpenAI(api_key=s.openai_api_key)
    completion = await client.chat.completions.create(
        model=s.llm_model,
        temperature=0.25,
        messages=[
            {"role": "system", "content": SISTEMA_MAASTRICHT + tom},
            {"role": "user", "content":
                f"Respostas da entrevista:\n{corpo}\n\n"
                f"Trechos do acervo (T1..Tk):\n{contexto}\n\n"
                "Escreva agora a formulação em Markdown, cerca de 500-800 palavras."},
        ],
    )
    return SaidaGerada(
        texto=(completion.choices[0].message.content or "").strip(),
        provider_id=f"openai:{s.llm_model}",
        hits=hits,
    )


# --------------------------------------------------------------------------
# WRAP → plano estruturado
# --------------------------------------------------------------------------

SISTEMA_WRAP = """Você é o assistente clínico do Práxis (CENAT), coescrevendo um
**plano WRAP** (Wellness Recovery Action Plan) a partir das respostas de
paciente/profissional.

Diretrizes:

1. WRAP é um plano da PESSOA, não um documento clínico prescritivo.
   Escreva em primeira pessoa (linguagem da pessoa que fez o plano).
2. Preserve os conteúdos exatos que a pessoa trouxe; complete apenas
   lacunas óbvias com sugestões cuidadosas, marcando como *(sugestão a
   validar)*.
3. Estruture em Markdown com estes cabeçalhos:
   ## Como é estar bem
   ## Caixa de ferramentas de bem-estar
   ## Gatilhos e resposta
   ## Sinais de alerta precoces
   ## Quando as coisas pioram
   ## Plano de crise
   ## Pós-crise
4. Encerre com:
   *"Este plano é um instrumento pessoal. Revise-o periodicamente com
   quem cuida de você."*
"""


async def planejar_wrap(
    definicao: dict[str, Any],
    respostas: dict[str, Any],
) -> SaidaGerada:
    s = get_settings()
    corpo = _flatten_respostas(definicao, respostas)

    client = AsyncOpenAI(api_key=s.openai_api_key)
    completion = await client.chat.completions.create(
        model=s.llm_model,
        temperature=0.2,
        messages=[
            {"role": "system", "content": SISTEMA_WRAP},
            {"role": "user", "content":
                f"Respostas construídas pelo(a) paciente / profissional:\n{corpo}\n\n"
                "Escreva agora o plano WRAP em Markdown, na primeira pessoa,"
                " ~400-700 palavras."},
        ],
    )
    return SaidaGerada(
        texto=(completion.choices[0].message.content or "").strip(),
        provider_id=f"openai:{s.llm_model}",
        hits=[],
    )


# --------------------------------------------------------------------------
# Escalas Likert (likert_sum) → leitura clínica curta sobre o escore FACTUAL
# --------------------------------------------------------------------------

SISTEMA_LIKERT = """Você é o assistente clínico do Práxis (CENAT). Uma escala
psicométrica de autorrelato foi respondida e o **escore e a faixa já foram
calculados de forma determinística pelo sistema** — são FACTUAIS.

Regras absolutas:
1. NUNCA recalcule, questione ou altere o escore/faixa fornecidos. Use os
   números exatamente como estão.
2. NÃO é diagnóstico. Escala é rastreio/apoio; escreva uma leitura clínica
   BREVE (~120-200 palavras) que contextualize o escore e a faixa.
3. Se houver subescalas, comente cada uma pela sua faixa.
4. Se algum item de risco (ex.: ideação) estiver sinalizado, oriente avaliação
   de segurança — sem alarmismo, como próximo passo clínico.
5. Markdown com os cabeçalhos:
   ## Leitura do escore
   ## Pontos de atenção
   ## Próximos passos sugeridos (sugestões, não prescrição)
6. Feche com:
   *"O escore é calculado (factual); esta leitura é apoio ao raciocínio clínico.
   A responsabilidade técnica pela conduta é do profissional (Manual CFP 2025)."*
"""


def _resumo_pontuacao(definicao: dict[str, Any], pont: dict[str, Any]) -> str:
    """Texto compacto e factual do escore/faixa para embasar o prompt."""
    linhas: list[str] = []
    if pont.get("tipo") == "subescalas":
        for sub in pont.get("subescores", []):
            estado = "" if sub.get("completo") else " (incompleta)"
            linhas.append(
                f"- {sub['rotulo']}: escore {sub['escore']} → "
                f"faixa **{sub.get('faixa_rotulo') or 'n/d'}**{estado} "
                f"[{sub['itens_respondidos']}/{sub['total_itens']} itens]"
            )
    else:
        transf = pont.get("transformado")
        base = f"escore {pont.get('escore')}"
        if transf is not None:
            base = f"escore transformado {transf} (bruto {pont.get('escore_bruto')})"
        estado = "" if pont.get("completo") else " (incompleto)"
        linhas.append(
            f"- {base} → faixa **{pont.get('faixa_rotulo') or 'n/d'}**{estado} "
            f"[{pont.get('itens_respondidos')}/{pont.get('total_itens')} itens]"
        )
    # sinaliza itens de risco respondidos positivamente
    return "\n".join(linhas)


async def redigir_leitura_escala(
    titulo: str,
    definicao: dict[str, Any],
    pontuacao: dict[str, Any],
    respostas: dict[str, Any],
) -> SaidaGerada:
    s = get_settings()

    # Flags de risco marcadas no definicao e respondidas com valor > 0.
    respmap = (respostas or {}).get("itens", {}) or {}
    riscos = [
        it["texto"] for it in definicao.get("itens", [])
        if it.get("flag") == "risco" and (respmap.get(it["id"]) or 0)
    ]
    alerta = ("\n\nSINAL DE RISCO sinalizado no(s) item(ns): "
              + "; ".join(riscos)) if riscos else ""

    client = AsyncOpenAI(api_key=s.openai_api_key)
    completion = await client.chat.completions.create(
        model=s.llm_model,
        temperature=0.2,
        messages=[
            {"role": "system", "content": SISTEMA_LIKERT},
            {"role": "user", "content":
                f"Instrumento: {titulo}\n\n"
                f"Escore/faixa (FACTUAIS, já calculados):\n{_resumo_pontuacao(definicao, pontuacao)}"
                f"{alerta}\n\n"
                "Escreva a leitura clínica breve em Markdown."},
        ],
    )
    return SaidaGerada(
        texto=(completion.choices[0].message.content or "").strip(),
        provider_id=f"openai:{s.llm_model}",
        hits=[],
    )
