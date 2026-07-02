"""Conformidade IA-CFP — transparência de IA (Res. CFP 09/2024).

Fonte única de:
- TCLE de uso de IA (texto versionado, registrado via `consentimentos`);
- mapa de ações de IA no audit_log → recurso legível;
- consulta factual do log de uso de IA por paciente (reusa o audit_log,
  filtrando por `meta.paciente_id`).

Sem tabela nova: o log é derivado dos eventos reais já registrados.
"""
from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog

# --------------------------------------------------------------------------
# TCLE de uso de IA — texto versionado (o texto exato aceito é persistido em
# consentimentos.texto_aceito, o que registra a versão de forma imutável).
# --------------------------------------------------------------------------

TCLE_IA_VERSAO = "v1"

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
    "2. A responsabilidade técnica pela conduta é do(a) profissional (Res. CFP "
    "09/2024).\n"
    "3. Meus dados são tratados com confidencialidade e conforme a LGPD; dados "
    "identificáveis não são enviados à IA para além do estritamente necessário "
    "ao apoio.\n"
    "4. Posso solicitar esclarecimentos e revogar esta autorização a qualquer "
    "momento, sem prejuízo do meu atendimento.\n\n"
    "Declaro ter sido informado(a) de forma clara e que concordo com o uso de IA "
    "de apoio nos termos acima."
)


def tcle_ia() -> dict[str, str]:
    return {"versao": TCLE_IA_VERSAO, "texto": TCLE_IA_TEXTO}


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
