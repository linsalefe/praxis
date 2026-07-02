"""Prompt e chamada ao LLM (GPT-5.1-mini) com guardrails clínicos."""
from __future__ import annotations

import re
from collections.abc import AsyncIterator
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
2. **Referencie os trechos inline** com o marcador `[Tn]` (ex.: `[T2]`) logo após a
   informação que veio daquele trecho. **NÃO** escreva uma seção "Fontes:" ao final
   nem liste as referências — a interface do Práxis exibe as fontes automaticamente.
3. Para trechos marcados como **[TERCEIRO]** (obras que não são da editora CENAT),
   **NUNCA transcreva o texto literalmente**. Parafraseie a ideia com suas
   palavras e cite normalmente. Não copie frases inteiras dos trechos.
4. Tom: técnico-clínico, respeitoso, sem prometer resultados. Evite diagnósticos
   assertivos ou prescrição medicamentosa.
5. **NÃO** escreva disclaimers, avisos de responsabilidade ou notas de rodapé — a
   interface já exibe o aviso clínico. Encerre no próprio conteúdo clínico.
6. Escreva em **português do Brasil**, direto ao ponto (200-500 palavras).
"""


@dataclass
class Resposta:
    resposta: str
    sem_respaldo: bool
    modelo: str


# --- Strip defensivo: garante um único bloco de fontes e um único disclaimer ---
# A interface exibe as fontes (chips) e o disclaimer (rodapé). Se o modelo ainda
# assim escrever uma seção "Fontes:" final ou o disclaimer no corpo, removemos.
# Conservador: só corta a partir de um cabeçalho "Fontes:" em início de linha ou
# do início conhecido do disclaimer — nunca no meio do conteúdo clínico.
_RE_FONTES = re.compile(r"\n\s*\*{0,2}\s*Fontes\s*:", re.IGNORECASE)
_RE_DISCLAIMER = re.compile(r"\*{0,2}_{0,2}Esta resposta é apoio ao racioc", re.IGNORECASE)


def _corte(texto: str) -> int | None:
    """Índice do início do primeiro bloco a remover (Fontes: ou disclaimer), ou None."""
    idxs = [m.start() for m in (_RE_FONTES.search(texto), _RE_DISCLAIMER.search(texto)) if m]
    return min(idxs) if idxs else None


def _limpar_corpo(texto: str) -> str:
    """Remove seção de fontes final e/ou disclaimer do corpo gerado."""
    corte = _corte(texto)
    return texto[:corte].rstrip() if corte is not None else texto.rstrip()


# Cauda segura: nunca emitimos os últimos N chars até termos certeza de que não são
# o começo de um marcador ("\n**Fontes:" ~10 chars; prefixo do disclaimer ~40 chars).
_HOLD = 64


async def _stream_limpo(agen: AsyncIterator[str]) -> AsyncIterator[str]:
    """Filtra o stream do LLM emitindo apenas o corpo clínico: detecta o começo de
    'Fontes:'/disclaimer e para; segura uma cauda de _HOLD chars para não vazar um
    marcador parcial na fronteira entre deltas."""
    acc = ""
    emitido = 0
    parou = False
    async for delta in agen:
        acc += delta
        if parou:
            continue
        corte = _corte(acc)
        if corte is not None:
            if corte > emitido:
                yield acc[emitido:corte]
                emitido = corte
            parou = True
            continue
        limite = len(acc) - _HOLD
        if limite > emitido:
            yield acc[emitido:limite]
            emitido = limite
    if not parou:
        final = _limpar_corpo(acc)
        if len(final) > emitido:
            yield final[emitido:]


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


def calcular_sem_respaldo(hits: list[Hit]) -> bool:
    s = get_settings()
    return not hits or max((h.similaridade for h in hits), default=0.0) < s.rag_sim_min


def _montar_mensagens(pergunta: str, hits: list[Hit], sobre_paciente: bool) -> list[dict[str, str]]:
    """Monta as mensagens do LLM — mesmo prompt/guardrails para stream e não-stream."""
    aviso_paciente = ""
    if sobre_paciente:
        aviso_paciente = (
            "\n\nO psicólogo indicou que a pergunta é sobre um caso específico. "
            "Por política de privacidade (LGPD), NÃO recebemos dados do paciente. "
            "Responda de forma genérica e sugira como aplicar clinicamente."
        )

    contexto = _formatar_contexto(hits) if hits else "(nenhum trecho relevante encontrado no acervo)"
    if calcular_sem_respaldo(hits):
        contexto += (
            "\n\n(Atenção: nenhum trecho com similaridade suficiente. "
            "Você deve avisar o usuário que o acervo não sustenta esta resposta.)"
        )

    return [
        {"role": "system", "content": SISTEMA + aviso_paciente},
        {
            "role": "user",
            "content": (
                f"Pergunta do profissional:\n{pergunta}\n\n"
                f"Trechos do acervo (referências T1..Tk):\n\n{contexto}"
            ),
        },
    ]


async def responder(pergunta: str, hits: list[Hit], sobre_paciente: bool = False) -> Resposta:
    s = get_settings()
    client = AsyncOpenAI(api_key=s.openai_api_key)
    completion = await client.chat.completions.create(
        model=s.llm_model,
        messages=_montar_mensagens(pergunta, hits, sobre_paciente),
        temperature=0.2,
    )
    return Resposta(
        resposta=_limpar_corpo((completion.choices[0].message.content or "").strip()),
        sem_respaldo=calcular_sem_respaldo(hits),
        modelo=s.llm_model,
    )


async def responder_stream(
    pergunta: str, hits: list[Hit], sobre_paciente: bool = False
) -> AsyncIterator[str]:
    """Versão streaming de `responder`: mesmo prompt/guardrails, emite os deltas
    de texto conforme o LLM gera. Citações/sem_respaldo/modelo são derivados dos
    hits pelo chamador (conhecidos antes da geração)."""
    s = get_settings()
    client = AsyncOpenAI(api_key=s.openai_api_key)
    stream = await client.chat.completions.create(
        model=s.llm_model,
        messages=_montar_mensagens(pergunta, hits, sobre_paciente),
        temperature=0.2,
        stream=True,
    )

    async def _deltas() -> AsyncIterator[str]:
        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    async for texto in _stream_limpo(_deltas()):
        yield texto
