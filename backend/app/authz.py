"""Autorização por profissional dentro do tenant (P1 — sigilo na clínica).

Regra de sigilo:
- `owner`  → enxerga todos os pacientes do tenant (visão de administrador da clínica);
- `profissional` → enxerga apenas os pacientes de que é dono (`Paciente.criado_por`);
- `secretaria` → não acessa prontuário (rotas clínicas negam).

A fonte da verdade do dono é `Paciente.criado_por` (NOT NULL, gravado na criação),
então não há migração de dado. Reforço em profundidade fica na camada de aplicação;
RLS no Postgres é uma evolução futura.
"""
from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.paciente import Paciente
from app.models.user import User

# Papéis com acesso a prontuário/dados clínicos.
PAPEIS_CLINICOS = {"owner", "profissional"}


def is_owner(user: User) -> bool:
    return user.papel == "owner"


def acessa_prontuario(user: User) -> bool:
    return user.papel in PAPEIS_CLINICOS


def escopo_paciente_clause(user: User):
    """Cláusula WHERE de dono para queries que envolvem `Paciente`.

    Retorna None para owner (sem restrição extra além do tenant). Para
    profissional, restringe a `Paciente.criado_por == user.id`. Use assim:

        q = select(...).where(Algo.tenant_id == user.tenant_id)
        if (c := escopo_paciente_clause(user)) is not None:
            q = q.where(c)
    """
    if is_owner(user):
        return None
    return Paciente.criado_por == user.id


def pode_acessar_paciente(user: User, pac: Paciente) -> bool:
    return is_owner(user) or pac.criado_por == user.id


async def carregar_paciente(session: AsyncSession, user: User, paciente_id) -> Paciente:
    """Carrega um paciente do tenant do usuário, não deletado, respeitando o
    escopo por profissional. Levanta 404 (não vaza existência) se não existir,
    for de outro tenant, estiver deletado ou pertencer a outro profissional.
    """
    try:
        pid = paciente_id if isinstance(paciente_id, uuid.UUID) else uuid.UUID(str(paciente_id))
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "paciente_id inválido")
    pac = await session.get(Paciente, pid)
    if (
        pac is None
        or pac.tenant_id != user.tenant_id
        or pac.deleted_at is not None
        or not pode_acessar_paciente(user, pac)
    ):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Paciente não encontrado")
    return pac
