"""Conformidade IA-CFP — transparência de IA.

Não existe resolução específica do CFP sobre IA: o uso de IA na Psicologia é
orientado pela Nota de Posicionamento do CFP sobre Inteligência Artificial
(julho/2025) e pela Cartilha 2025. A responsabilidade técnica do psicólogo
decorre do Código de Ética Profissional. (A Res. CFP 09/2024 rege o
teleatendimento/TDICs — ver `routers/sessoes.py` —, não a IA.)

Fonte única de:
- TCLE de uso de IA (texto versionado, registrado via `consentimentos`);
- mapa de ações de IA no audit_log → recurso legível;
- consulta factual do log de uso de IA por paciente (reusa o audit_log,
  filtrando por `meta.paciente_id`).

Sem tabela nova: o log é derivado dos eventos reais já registrados.
"""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.consentimento import Consentimento

# --------------------------------------------------------------------------
# TCLE de uso de IA — texto versionado (o texto exato aceito é persistido em
# consentimentos.texto_aceito, o que registra a versão de forma imutável).
# --------------------------------------------------------------------------

TCLE_IA_VERSAO = "v2"

TCLE_IA_TEXTO = (
    "AUTORIZAÇÃO PARA USO DE INTELIGÊNCIA ARTIFICIAL DE APOIO (TCLE-IA " + TCLE_IA_VERSAO + ")\n\n"
    "Autorizo que, no meu atendimento, o(a) profissional utilize recursos de "
    "inteligência artificial de APOIO oferecidos pela plataforma Práxis (CENAT), "
    "a saber:\n"
    "• transcrição/estruturação de rascunhos de evolução (Scribe);\n"
    "• assistente de raciocínio clínico com base no acervo (Sofia);\n"
    "• apoio à preparação de sessão e à interpretação de instrumentos.\n\n"
    "Estou ciente de que:\n"
    "1. A IA é ferramenta de APOIO e produz apenas RASCUNHOS. O(a) profissional "
    "revisa, edita e ASSINA todo conteúdo — a IA não decide nem substitui o "
    "julgamento profissional.\n"
    "2. A responsabilidade técnica pela conduta é do(a) profissional, conforme o "
    "Código de Ética Profissional do Psicólogo e a Nota de Posicionamento do CFP "
    "sobre Inteligência Artificial (2025).\n"
    "3. Para viabilizar esses recursos, dados do meu atendimento — incluindo o "
    "ÁUDIO da sessão, quando eu uso o Scribe, e trechos de texto do prontuário — "
    "são processados por provedor de IA subcontratado (sub-processador) localizado "
    "nos ESTADOS UNIDOS (OpenAI), o que caracteriza TRANSFERÊNCIA INTERNACIONAL de "
    "dados (LGPD art. 33). Isso ocorre com base no meu CONSENTIMENTO e apenas para "
    "a finalidade de apoio acima; o áudio é apagado após a transcrição e não é "
    "usado para treinar modelos.\n"
    "4. Meus dados são tratados com confidencialidade e conforme a LGPD, limitados "
    "ao estritamente necessário ao apoio.\n"
    "5. Posso solicitar esclarecimentos e revogar esta autorização a qualquer "
    "momento, sem prejuízo do meu atendimento.\n\n"
    "Declaro ter sido informado(a) de forma clara e que concordo com o uso de IA "
    "de apoio nos termos acima."
)


def tcle_ia() -> dict[str, str]:
    return {"versao": TCLE_IA_VERSAO, "texto": TCLE_IA_TEXTO}


# --------------------------------------------------------------------------
# Gate de consentimento — reutilizável pelos fluxos de IA e por telessessão.
# "Ativo" = existe consentimento do tipo E não foi revogado (revogado_em IS NULL).
# --------------------------------------------------------------------------

async def consentimento_ativo(
    session: AsyncSession, tenant_id, paciente_id, tipo: str
) -> Consentimento | None:
    """Consentimento não-revogado do `tipo` para o paciente (ou None)."""
    return await session.scalar(
        select(Consentimento).where(
            Consentimento.tenant_id == tenant_id,
            Consentimento.paciente_id == paciente_id,
            Consentimento.tipo == tipo,
            Consentimento.revogado_em.is_(None),
        )
    )


async def exigir_uso_ia(session: AsyncSession, tenant_id, paciente_id) -> None:
    """Gate CFP/LGPD: bloqueia geração de IA por paciente sem `uso_ia` ativo.

    Aplicado a todo fluxo de IA vinculado a um paciente (Scribe, Sofia com
    paciente, Preparação, Instrumentos). Mensagem 403 indica como registrar.
    """
    if await consentimento_ativo(session, tenant_id, paciente_id, "uso_ia") is None:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Sem consentimento de uso de IA ('uso_ia') ativo para este paciente. "
            "Registre o TCLE de uso de IA (aba Conformidade IA do paciente) antes "
            "de usar recursos de IA neste caso.",
        )


# --------------------------------------------------------------------------
# Ações de IA no audit_log → recurso legível para o paciente.
# --------------------------------------------------------------------------

ACOES_IA: dict[str, str] = {
    "SOFIA_ASK": "Sofia — assistente de raciocínio clínico",
    "SCRIBE_STRUCTURED": "Scribe — rascunho de evolução",
    "ROTEIRO_GERADO": "Preparação de sessão",
    "INSTRUMENTO_SAIDA_GERADA": "Instrumento — saída interpretada",
}


async def listar_ia_log(session: AsyncSession, tenant_id, paciente_id) -> list[dict]:
    """Eventos reais de uso de IA para o paciente (factual, a partir do audit_log).

    Filtra por `meta.paciente_id` — cobre os eventos marcados a partir desta
    versão. Ordenado do mais recente para o mais antigo.
    """
    q = (
        select(AuditLog.acao, AuditLog.ts, AuditLog.entidade, AuditLog.entidade_id)
        .where(
            AuditLog.tenant_id == tenant_id,
            AuditLog.acao.in_(list(ACOES_IA.keys())),
            AuditLog.meta["paciente_id"].astext == str(paciente_id),
        )
        .order_by(desc(AuditLog.ts))
    )
    rows = (await session.execute(q)).all()
    return [
        {
            "acao": acao,
            "recurso": ACOES_IA.get(acao, acao),
            "ts": ts.isoformat() if ts else None,
            "entidade": entidade,
            "entidade_id": entidade_id,
        }
        for acao, ts, entidade, entidade_id in rows
    ]
