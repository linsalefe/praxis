"""Audit logging automático via eventos SQLAlchemy.

Sempre que uma entidade auditável é inserida/atualizada/removida, um registro é
gravado em `audit_log` na mesma sessão, capturando `user_id`/`tenant_id`/`ip` do
contexto do request.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import current_request_ip, current_tenant_id, current_user_id
from app.models.audit import AuditLog
from app.models.consentimento import Consentimento
from app.models.evolucao import Evolucao
from app.models.paciente import Paciente
from app.models.sessao import Sessao

AUDITABLE = {
    Paciente: "Paciente",
    Sessao: "Sessao",
    Evolucao: "Evolucao",
    Consentimento: "Consentimento",
}


def _make_entry(action: str, obj: Any, entidade_nome: str, extra: dict | None = None) -> AuditLog:
    tenant_id = getattr(obj, "tenant_id", None) or current_tenant_id.get()
    return AuditLog(
        tenant_id=tenant_id,
        user_id=current_user_id.get(),
        acao=action,
        entidade=entidade_nome,
        entidade_id=str(getattr(obj, "id", "")) or None,
        ip=current_request_ip.get(),
        meta=extra or {},
    )


def install(session: AsyncSession) -> None:
    """Instala hooks numa sessão async ligando aos eventos do Session sync subjacente."""

    sync_session = session.sync_session

    @event.listens_for(sync_session, "before_flush")
    def _before_flush(sess, flush_context, instances):  # noqa: ANN001
        new_entries: list[AuditLog] = []

        for obj in sess.new:
            cls = type(obj)
            if cls in AUDITABLE:
                new_entries.append(_make_entry("CREATE", obj, AUDITABLE[cls]))

        for obj in sess.dirty:
            cls = type(obj)
            if cls in AUDITABLE and sess.is_modified(obj, include_collections=False):
                new_entries.append(_make_entry("UPDATE", obj, AUDITABLE[cls]))

        for obj in sess.deleted:
            cls = type(obj)
            if cls in AUDITABLE:
                new_entries.append(_make_entry("DELETE", obj, AUDITABLE[cls]))

        for e in new_entries:
            sess.add(e)
