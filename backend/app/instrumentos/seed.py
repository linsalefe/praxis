"""Upsert das definições do catálogo em `instrumentos` no startup.

Idempotente: compara (tipo, versao). Se a versão mudou, atualiza definição
sem tocar em respostas_instrumento existentes.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.instrumentos.definitions import CATALOGO
from app.models.instrumentos import Instrumento


async def upsert_catalogo(session: AsyncSession) -> int:
    changed = 0
    for spec in CATALOGO:
        instr = await session.scalar(select(Instrumento).where(Instrumento.tipo == spec["tipo"]))
        if instr is None:
            instr = Instrumento(
                tipo=spec["tipo"],
                versao=spec["versao"],
                titulo=spec["titulo"],
                descricao=spec.get("descricao"),
                fonte=spec.get("fonte"),
                definicao=spec["definicao"],
            )
            session.add(instr)
            changed += 1
        elif instr.versao != spec["versao"] or instr.definicao != spec["definicao"]:
            instr.versao = spec["versao"]
            instr.titulo = spec["titulo"]
            instr.descricao = spec.get("descricao")
            instr.fonte = spec.get("fonte")
            instr.definicao = spec["definicao"]
            changed += 1
    if changed:
        await session.commit()
    return changed
