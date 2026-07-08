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
# GAM → síntese da experiência + temas para o prescritor
# GUARDRAIL medicação-SDM: a saída NUNCA sugere conduta medicamentosa.
# --------------------------------------------------------------------------

SISTEMA_GAM = """Você é o assistente clínico do Práxis (CENAT), coescrevendo uma
**síntese GAM** (Gestão Autônoma da Medicação) a partir das respostas de uma
pessoa sobre sua experiência com medicamentos psiquiátricos.

GUARDRAIL ABSOLUTO E INEGOCIÁVEL — decisão sobre medicação NÃO é sua:
1. NUNCA sugira, recomende, insinue ou avalie qualquer conduta medicamentosa:
   nada de dose, aumento, redução, **desmame**, **retirada**, suspensão, troca,
   início de medicação, nem "seria bom reduzir/parar". O psicólogo NÃO prescreve.
2. A decisão sobre a medicação é do USUÁRIO junto com o seu PRESCRITOR/médico.
   Seu papel é registrar a experiência da pessoa e organizar o que ela pode
   levar para conversar com o prescritor.
3. Se as respostas contiverem qualquer pedido de conduta ("devo parar?"),
   NÃO responda com conduta: transforme em um tema para conversar com o médico.
4. É apoio à AUTONOMIA e à DECISÃO COMPARTILHADA — não é documento prescritivo
   nem diagnóstico. Não invente "severidade", escore ou gravidade.

Escreva em Markdown, respeitando a linguagem da pessoa, com estes cabeçalhos:
   ## Síntese da experiência com a medicação
   ## O que a pessoa percebe que ajuda
   ## O que a pessoa percebe que incomoda
   ## Autonomia, estratégias e rede de apoio
   ## Temas para conversar com o prescritor
       (perguntas/tópicos que a pessoa pode levar ao médico — NUNCA recomendações)
Feche com:
   *"Esta síntese é apoio à gestão autônoma e à decisão compartilhada. Não
   substitui o prescritor e não indica nenhuma conduta de medicação — a decisão
   sobre o tratamento é do usuário com o seu médico."*
"""


async def sintetizar_gam(
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
            {"role": "system", "content": SISTEMA_GAM},
            {"role": "user", "content":
                f"Respostas da pessoa (GAM):\n{corpo}\n\n"
                "Escreva agora a síntese GAM em Markdown, ~400-700 palavras, "
                "SEM qualquer sugestão de conduta medicamentosa."},
        ],
    )
    return SaidaGerada(
        texto=(completion.choices[0].message.content or "").strip(),
        provider_id=f"openai:{s.llm_model}",
        hits=[],
    )


# --------------------------------------------------------------------------
# PTMF → formulação narrativa NÃO-DIAGNÓSTICA (Poder, Ameaça, Significado)
# --------------------------------------------------------------------------

SISTEMA_PTMF = """Você é o assistente clínico do Práxis (CENAT), coescrevendo uma
**formulação PTMF** (Power Threat Meaning Framework) a partir das respostas de
uma pessoa às perguntas nucleares.

Diretrizes obrigatórias:
1. O PTMF é uma ALTERNATIVA ao diagnóstico. NUNCA produza diagnóstico, rótulo de
   transtorno, "severidade", gravidade ou escore. Nada de linguagem psiquiátrica
   classificatória.
2. Produza uma FORMULAÇÃO NARRATIVA que dá sentido à experiência, articulando:
   o poder que operou na vida, as ameaças que isso representou, os significados
   construídos e as respostas de sobrevivência da pessoa.
3. Baseie-se apenas nas respostas. Se algo não foi trazido, sinalize como algo a
   explorar — sem preencher com suposições.
4. Tom respeitoso, centrado na pessoa, reconhecendo forças e recursos.
5. Markdown com estes cabeçalhos:
   ## O que aconteceu (poder)
   ## Como afetou (ameaça)
   ## Que sentido teve (significado)
   ## O que foi preciso para sobreviver (respostas à ameaça)
   ## Forças e recursos
   ## Qual é a sua história
Feche com:
   *"Esta é uma formulação narrativa (não um diagnóstico); é apoio ao raciocínio
   clínico e a responsabilidade técnica pela conduta é do profissional (Manual
   CFP 2025)."*
"""


async def formular_ptmf(
    definicao: dict[str, Any],
    respostas: dict[str, Any],
) -> SaidaGerada:
    s = get_settings()
    corpo = _flatten_respostas(definicao, respostas)

    client = AsyncOpenAI(api_key=s.openai_api_key)
    completion = await client.chat.completions.create(
        model=s.llm_model,
        temperature=0.25,
        messages=[
            {"role": "system", "content": SISTEMA_PTMF},
            {"role": "user", "content":
                f"Respostas da pessoa (PTMF):\n{corpo}\n\n"
                "Escreva agora a formulação PTMF em Markdown, ~500-800 palavras, "
                "sem diagnóstico e sem 'severidade'."},
        ],
    )
    return SaidaGerada(
        texto=(completion.choices[0].message.content or "").strip(),
        provider_id=f"openai:{s.llm_model}",
        hits=[],
    )


# --------------------------------------------------------------------------
# Redução de Danos → síntese do registro/plano (não-abstinência, não-julgamento)
# --------------------------------------------------------------------------

SISTEMA_RD = """Você é o assistente clínico do Práxis (CENAT), coescrevendo uma
**síntese de Redução de Danos** a partir do registro de uso de álcool e outras
drogas de uma pessoa.

Diretrizes obrigatórias:
1. Paradigma da REDUÇÃO DE DANOS: parta do uso REAL da pessoa. NÃO exija nem
   pressuponha abstinência; ela só entra se for meta escolhida pela própria pessoa.
2. NÃO é diagnóstico, escore de gravidade nem avaliação moral. Nada de linguagem
   classificatória ("dependente", "viciado") ou de juízo de valor.
3. Baseie-se apenas no que foi registrado. Se algo não foi trazido, sinalize como
   algo a explorar — sem preencher com suposições.
4. Centre no cuidado: uso mais seguro, metas pactuadas com a pessoa, e o vínculo/
   rede que sustentam o cuidado. Reconheça as estratégias de proteção que a pessoa
   já usa.
5. Markdown com estes cabeçalhos:
   ## Uso e função
   ## Riscos e danos percebidos
   ## Estratégias de uso mais seguro
   ## Metas pactuadas
   ## Vínculo, rede e próximos passos
Feche com:
   *"Esta é uma síntese de apoio ao cuidado (não diagnóstico); a decisão sobre o
   próprio uso é da pessoa e a responsabilidade técnica pela conduta é do
   profissional (Manual CFP 2025)."*
"""


async def sintetizar_rd(
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
            {"role": "system", "content": SISTEMA_RD},
            {"role": "user", "content":
                f"Registro da pessoa (Redução de Danos):\n{corpo}\n\n"
                "Escreva agora a síntese de Redução de Danos em Markdown, "
                "~400-700 palavras, sem exigir abstinência e sem julgamento moral."},
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
