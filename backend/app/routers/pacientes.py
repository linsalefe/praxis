"""CRUD de Paciente — PII cifrada em repouso, isolamento por tenant."""
from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.authz import carregar_paciente, escopo_paciente_clause
from app.conformidade.ia_cfp import listar_ia_log
from app.deps import SessionDep, get_current_user
from app.models.audit import AuditLog
from app.models.paciente import Paciente
from app.models.user import User
from app.schemas.clinico import IaLogItemOut, PacienteCreate, PacienteOut, PacienteUpdate
from app.security.crypto import decrypt_str, encrypt_str

router = APIRouter(prefix="/pacientes", tags=["pacientes"])


def _to_out(p: Paciente) -> PacienteOut:
    nasc_str = decrypt_str(p.nascimento_cifrado)
    return PacienteOut(
        id=str(p.id),
        nome=decrypt_str(p.nome_cifrado) or "",
        contato=decrypt_str(p.contato_cifrado),
        nascimento=date.fromisoformat(nasc_str) if nasc_str else None,
        documento=decrypt_str(p.documento_cifrado),
        sexo=p.sexo,
        criado_em=p.criado_em,
        atualizado_em=p.atualizado_em,
    )


@router.post("", response_model=PacienteOut, status_code=status.HTTP_201_CREATED)
async def criar(
    body: PacienteCreate,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> PacienteOut:
    p = Paciente(
        tenant_id=user.tenant_id,
        nome_cifrado=encrypt_str(body.nome),
        contato_cifrado=encrypt_str(body.contato) if body.contato else None,
        nascimento_cifrado=encrypt_str(body.nascimento.isoformat()) if body.nascimento else None,
        documento_cifrado=encrypt_str(body.documento) if body.documento else None,
        sexo=body.sexo,
        criado_por=user.id,
    )
    session.add(p)
    await session.commit()
    await session.refresh(p)
    return _to_out(p)


@router.get("", response_model=list[PacienteOut])
async def listar(
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> list[PacienteOut]:
    q = select(Paciente).where(
        Paciente.tenant_id == user.tenant_id,
        Paciente.deleted_at.is_(None),
    ).order_by(Paciente.criado_em.desc())
    if (c := escopo_paciente_clause(user)) is not None:
        q = q.where(c)
    rows = list((await session.scalars(q)).all())
    # Auditar VIEW em lote.
    session.add(AuditLog(
        tenant_id=user.tenant_id, user_id=user.id, acao="VIEW",
        entidade="Paciente", entidade_id=None, meta={"count": len(rows)},
    ))
    await session.commit()
    return [_to_out(p) for p in rows]


@router.get("/{paciente_id}", response_model=PacienteOut)
async def obter(
    paciente_id: str,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> PacienteOut:
    p = await carregar_paciente(session, user, paciente_id)
    session.add(AuditLog(
        tenant_id=user.tenant_id, user_id=user.id, acao="VIEW",
        entidade="Paciente", entidade_id=str(p.id),
    ))
    await session.commit()
    return _to_out(p)


@router.patch("/{paciente_id}", response_model=PacienteOut)
async def atualizar(
    paciente_id: str,
    body: PacienteUpdate,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> PacienteOut:
    p = await carregar_paciente(session, user, paciente_id)

    if body.nome is not None:
        p.nome_cifrado = encrypt_str(body.nome)  # type: ignore[assignment]
    if body.contato is not None:
        p.contato_cifrado = encrypt_str(body.contato)
    if body.nascimento is not None:
        p.nascimento_cifrado = encrypt_str(body.nascimento.isoformat())
    if body.documento is not None:
        p.documento_cifrado = encrypt_str(body.documento)
    if body.sexo is not None:
        p.sexo = body.sexo

    await session.commit()
    await session.refresh(p)
    return _to_out(p)


@router.delete("/{paciente_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deletar(
    paciente_id: str,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> None:
    from datetime import datetime, timezone

    p = await carregar_paciente(session, user, paciente_id)

    # Soft-delete respeitando guarda de prontuário (20 anos).
    from datetime import timedelta
    p.deleted_at = datetime.now(tz=timezone.utc)
    p.reter_ate = (datetime.now(tz=timezone.utc) + timedelta(days=365 * 20)).date()
    await session.commit()


@router.get("/{paciente_id}/ia-log", response_model=list[IaLogItemOut])
async def ia_log(
    paciente_id: str,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> list[IaLogItemOut]:
    """Log factual de uso de IA para este paciente (Nota de Posicionamento CFP sobre IA, 2025)."""
    p = await carregar_paciente(session, user, paciente_id)
    itens = await listar_ia_log(session, user.tenant_id, p.id)
    return [IaLogItemOut(**it) for it in itens]
