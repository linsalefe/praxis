"""Monta um retrato ANONIMIZADO do paciente para o LLM de preparação.

Regras rígidas de anonimização:
- NÃO envia nome, contato, documento, nascimento em texto claro.
- Idade convertida para faixa etária.
- Referência à pessoa sempre como "o paciente" / "a pessoa".
- Envia texto das últimas evoluções assinadas e saídas markdown dos
  últimos instrumentos finalizados — dado clínico agregado, sem PII.

A anonimização acontece aqui no server; o retorno já vem sem PII.
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timezone

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evolucao import Evolucao
from app.models.instrumentos import Instrumento, RespostaInstrumento
from app.models.paciente import Paciente
from app.models.sessao import Sessao
from app.security.crypto import decrypt_str

MAX_EVOLUCOES = 5
MAX_INSTRUMENTOS = 2
CHARS_BY_EVOLUCAO = 1400
CHARS_BY_INSTRUMENTO = 1800

# Padrões de expressões que indicam nome próprio no texto — para limpeza.
_RE_QUEBRA = re.compile(r"\s+")


def _faixa_etaria(iso_nasc: str | None) -> str | None:
    if not iso_nasc:
        return None
    try:
        d = date.fromisoformat(iso_nasc)
    except ValueError:
        return None
    hoje = date.today()
    anos = hoje.year - d.year - ((hoje.month, hoje.day) < (d.month, d.day))
    if anos < 0 or anos > 120:
        return None
    if anos < 12:
        return "criança (<12)"
    if anos < 18:
        return "adolescente (12-17)"
    if anos < 25:
        return "jovem adulto (18-24)"
    if anos < 40:
        return "adulto (25-39)"
    if anos < 60:
        return "adulto (40-59)"
    return "idoso (60+)"


def _mascarar_nome(texto: str, nome_completo: str) -> str:
    """Substitui QUALQUER token do nome completo por '[paciente]'.

    Cobre primeiro nome, sobrenomes compostos (separados por espaço ou hífen),
    case-insensitive. Descarta tokens com menos de 3 caracteres para não
    tocar em preposições ('de', 'da', 'do').
    """
    if not texto or not nome_completo:
        return texto or ""
    tokens = [t for t in re.split(r"[\s\-]+", nome_completo.strip()) if len(t) >= 3]
    # Ordena por comprimento decrescente para mascarar os mais específicos primeiro.
    tokens.sort(key=len, reverse=True)
    for tok in tokens:
        padrao = re.compile(rf"\b{re.escape(tok)}\b", flags=re.IGNORECASE)
        texto = padrao.sub("[paciente]", texto)
    return texto


@dataclass
class ContextoAnonimo:
    """Estrutura pronta para injeção no prompt — SEM PII."""

    faixa_etaria: str | None
    sexo: str | None
    tempo_acompanhamento_dias: int | None
    n_sessoes: int
    n_evolucoes_assinadas: int
    n_instrumentos_finalizados: int
    evolucoes_texto: list[str] = field(default_factory=list)
    instrumentos_texto: list[str] = field(default_factory=list)

    def to_prompt_string(self) -> str:
        partes = [
            "## Retrato clínico agregado (anonimizado)",
            f"- Faixa etária: {self.faixa_etaria or 'não informada'}",
            f"- Sexo: {self.sexo or 'não informado'}",
            f"- Sessões registradas: {self.n_sessoes}",
            f"- Evoluções assinadas: {self.n_evolucoes_assinadas}",
            f"- Instrumentos finalizados: {self.n_instrumentos_finalizados}",
        ]
        if self.tempo_acompanhamento_dias is not None:
            partes.append(f"- Em acompanhamento há aproximadamente {self.tempo_acompanhamento_dias} dias")

        if self.evolucoes_texto:
            partes.append("\n## Últimas evoluções assinadas (mais recente primeiro)")
            for i, e in enumerate(self.evolucoes_texto, start=1):
                partes.append(f"\n### Evolução {i}\n{e}")

        if self.instrumentos_texto:
            partes.append("\n## Instrumentos finalizados (mais recente primeiro)")
            for i, s in enumerate(self.instrumentos_texto, start=1):
                partes.append(f"\n### Instrumento {i}\n{s}")

        return "\n".join(partes)


async def montar_contexto_anonimo(
    session: AsyncSession, paciente: Paciente
) -> ContextoAnonimo:
    """Descripta PII localmente para extrair metadados; NÃO retorna PII."""
    nome_claro = decrypt_str(paciente.nome_cifrado) or ""
    nasc = decrypt_str(paciente.nascimento_cifrado)
    faixa = _faixa_etaria(nasc)

    from sqlalchemy import func as _f
    n_sessoes = int(await session.scalar(
        select(_f.count()).select_from(Sessao).where(Sessao.paciente_id == paciente.id)
    ) or 0)
    # Evolucao chega ao paciente via Sessao.
    n_evol = int(await session.scalar(
        select(_f.count()).select_from(Evolucao)
        .join(Sessao, Sessao.id == Evolucao.sessao_id)
        .where(Sessao.paciente_id == paciente.id, Evolucao.assinado_em.is_not(None))
    ) or 0)
    n_instr = int(await session.scalar(
        select(_f.count()).select_from(RespostaInstrumento).where(
            RespostaInstrumento.paciente_id == paciente.id,
            RespostaInstrumento.status == "finalizado",
        )
    ) or 0)

    # tempo de acompanhamento (primeira sessão até hoje)
    primeira_data = await session.scalar(
        select(Sessao.data).where(Sessao.paciente_id == paciente.id)
        .order_by(Sessao.data.asc()).limit(1)
    )
    dias = None
    if primeira_data:
        delta = datetime.now(tz=timezone.utc) - primeira_data
        dias = int(delta.total_seconds() // 86400)

    # últimas evoluções assinadas
    evol_rows = list((await session.scalars(
        select(Evolucao)
        .join(Sessao, Sessao.id == Evolucao.sessao_id)
        .where(Sessao.paciente_id == paciente.id, Evolucao.assinado_em.is_not(None))
        .order_by(desc(Evolucao.assinado_em))
        .limit(MAX_EVOLUCOES)
    )).all())
    evolucoes_txt: list[str] = []
    for e in evol_rows:
        bloco = (
            f"- Assinada em {e.assinado_em.strftime('%Y-%m-%d') if e.assinado_em else 'n/d'}\n"
            f"- Identificação: {e.identificacao or '—'}\n"
            f"- Demanda/objetivos: {e.demanda_objetivos or '—'}\n"
            f"- Evolução: {e.evolucao or '—'}\n"
            f"- Encaminhamento: {e.encaminhamento or '—'}"
        )
        bloco = _mascarar_nome(bloco, nome_claro) if nome_claro else bloco
        if len(bloco) > CHARS_BY_EVOLUCAO:
            bloco = bloco[:CHARS_BY_EVOLUCAO] + "…"
        evolucoes_txt.append(bloco)

    # últimos instrumentos finalizados
    instr_rows = list((await session.scalars(
        select(RespostaInstrumento).where(
            RespostaInstrumento.paciente_id == paciente.id,
            RespostaInstrumento.status == "finalizado",
        ).order_by(desc(RespostaInstrumento.finalizado_em)).limit(MAX_INSTRUMENTOS)
    )).all())
    instrumentos_txt: list[str] = []
    for r in instr_rows:
        instr_defn = await session.get(Instrumento, r.instrumento_id)
        tipo = instr_defn.tipo if instr_defn else "?"
        finalizado_em = r.finalizado_em.strftime("%Y-%m-%d") if r.finalizado_em else "n/d"
        saida = r.saida_texto or ""
        if len(saida) > CHARS_BY_INSTRUMENTO:
            saida = saida[:CHARS_BY_INSTRUMENTO] + "…"
        bloco = f"- Tipo: {tipo} (finalizado em {finalizado_em})\n{saida}"
        bloco = _mascarar_nome(bloco, nome_claro) if nome_claro else bloco
        instrumentos_txt.append(bloco)

    return ContextoAnonimo(
        faixa_etaria=faixa,
        sexo=paciente.sexo,
        tempo_acompanhamento_dias=dias,
        n_sessoes=n_sessoes,
        n_evolucoes_assinadas=n_evol,
        n_instrumentos_finalizados=n_instr,
        evolucoes_texto=evolucoes_txt,
        instrumentos_texto=instrumentos_txt,
    )
