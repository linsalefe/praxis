"""Preparação de sessão — POST /sessao/preparar + CRUD de roteiros."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import desc, select

from app.conformidade.ia_cfp import exigir_uso_ia
from app.authz import carregar_paciente
from app.deps import SessionDep, get_current_user
from app.models.audit import AuditLog
from app.models.consentimento import Consentimento
from app.models.paciente import Paciente
from app.models.roteiro import RoteiroSessao
from app.models.sessao import Sessao
from app.models.user import User
from app.preparacao.contexto import montar_contexto_anonimo
from app.preparacao.roteiro import preparar_roteiro
from app.rag.retriever import Hit
from app.schemas.preparacao import (
    CitacaoOut,
    PrepararIn,
    RoteiroOut,
    RoteiroSalvarIn,
)

router = APIRouter(tags=["preparacao"])

SNIPPET_TERCEIRO = 180
SNIPPET_PROPRIO = 300


def _snippet(h: Hit) -> str:
    limit = SNIPPET_TERCEIRO if h.is_terceiro else SNIPPET_PROPRIO
    t = h.texto.strip().replace("\n", " ")
    return (t[:limit] + "…") if len(t) > limit else t


def _hits_to_dicts(hits: list[Hit]) -> list[dict]:
    """Serializa hits para JSONB (persistido no banco)."""
    out: list[dict] = []
    for i, h in enumerate(hits, start=1):
        out.append({
            "n": i,
            "documento_id": h.documento_id,
            "slug": h.slug,
            "titulo": h.titulo,
            "autor": h.autor,
            "editora": h.editora,
            "is_terceiro": h.is_terceiro,
            "capitulo": h.capitulo,
            "pagina_inicio": h.pagina_inicio,
            "pagina_fim": h.pagina_fim,
            "snippet": _snippet(h),
            "similaridade": round(h.similaridade, 3),
        })
    return out


def _citacoes_from_json(rows: list[dict]) -> list[CitacaoOut]:
    return [
        CitacaoOut(
            n=r["n"], documento_id=r["documento_id"], slug=r["slug"],
            titulo=r["titulo"], autor=r["autor"], is_terceiro=r["is_terceiro"],
            capitulo=r.get("capitulo"),
            pagina_inicio=r.get("pagina_inicio"), pagina_fim=r.get("pagina_fim"),
            snippet=r["snippet"], similaridade=r["similaridade"],
        )
        for r in rows
    ]


def _to_out(r: RoteiroSessao) -> RoteiroOut:
    return RoteiroOut(
        id=str(r.id), paciente_id=str(r.paciente_id),
        sessao_id=str(r.sessao_id) if r.sessao_id else None,
        autor_id=str(r.autor_id),
        texto=r.texto,
        citacoes=_citacoes_from_json(r.citacoes or []),
        provider=r.provider, meta=r.meta or {},
        criado_em=r.criado_em, atualizado_em=r.atualizado_em,
    )


async def _get_paciente(session, user: User, paciente_id: str) -> Paciente:
    # Escopo por profissional (P1): owner vê todos; profissional só os seus.
    return await carregar_paciente(session, user, paciente_id)


async def _valida_consentimento(session, tenant_id, paciente_id) -> None:
    cons = await session.scalar(
        select(Consentimento).where(
            Consentimento.tenant_id == tenant_id,
            Consentimento.paciente_id == paciente_id,
            Consentimento.tipo == "tratamento_dados",
            Consentimento.revogado_em.is_(None),
        )
    )
    if cons is None:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Sem consentimento LGPD 'tratamento_dados' registrado para este paciente. "
            "Registre o consentimento antes de gerar o roteiro de sessão.",
        )
    await exigir_uso_ia(session, tenant_id, paciente_id)


def _log(session, *, tenant_id, user_id, ip, acao, entidade, entidade_id, meta=None):
    session.add(AuditLog(
        tenant_id=tenant_id, user_id=user_id, ip=ip,
        acao=acao, entidade=entidade, entidade_id=entidade_id, meta=meta or {},
    ))


# --------------------------------------------------------------------------
# Rotas
# --------------------------------------------------------------------------

@router.post("/sessao/preparar", response_model=RoteiroOut,
             status_code=status.HTTP_201_CREATED)
async def preparar_sessao(
    body: PrepararIn,
    request: Request,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> RoteiroOut:
    pac = await _get_paciente(session, user, body.paciente_id)
    await _valida_consentimento(session, user.tenant_id, pac.id)

    # sessao_id opcional — se veio, valida ownership
    sessao_uuid: uuid.UUID | None = None
    if body.sessao_id:
        try:
            sessao_uuid = uuid.UUID(body.sessao_id)
        except ValueError:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "sessao_id inválido")
        s = await session.get(Sessao, sessao_uuid)
        if not s or s.tenant_id != user.tenant_id or s.paciente_id != pac.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Sessão não encontrada para esse paciente")

    ctx = await montar_contexto_anonimo(session, pac)
    roteiro = await preparar_roteiro(session, ctx, user.abordagem)

    r = RoteiroSessao(
        tenant_id=user.tenant_id, paciente_id=pac.id, sessao_id=sessao_uuid,
        autor_id=user.id, texto=roteiro.texto,
        citacoes=_hits_to_dicts(roteiro.hits),
        provider=roteiro.provider_id, meta=roteiro.meta,
    )
    session.add(r)
    await session.flush()

    ip = request.client.host if request.client else None
    _log(session, tenant_id=user.tenant_id, user_id=user.id, ip=ip,
         acao="ROTEIRO_GERADO", entidade="RoteiroSessao", entidade_id=str(r.id),
         meta={
             "provider": roteiro.provider_id,
             "n_evolucoes": ctx.n_evolucoes_assinadas,
             "n_instrumentos": ctx.n_instrumentos_finalizados,
             "n_chunks_acervo": len(roteiro.hits),
             "sessao_id": str(sessao_uuid) if sessao_uuid else None,
             "paciente_id": str(pac.id),
         })
    await session.commit()
    await session.refresh(r)
    return _to_out(r)


@router.get("/pacientes/{paciente_id}/roteiros", response_model=list[RoteiroOut])
async def listar_roteiros(
    paciente_id: str,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> list[RoteiroOut]:
    pac = await _get_paciente(session, user, paciente_id)
    rows = list((await session.scalars(
        select(RoteiroSessao)
        .where(RoteiroSessao.tenant_id == user.tenant_id, RoteiroSessao.paciente_id == pac.id)
        .order_by(desc(RoteiroSessao.criado_em))
        .limit(20)
    )).all())
    return [_to_out(r) for r in rows]


@router.get("/roteiros/{roteiro_id}", response_model=RoteiroOut)
async def obter_roteiro(
    roteiro_id: str,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> RoteiroOut:
    try:
        rid = uuid.UUID(roteiro_id)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "id inválido")
    r = await session.get(RoteiroSessao, rid)
    if not r or r.tenant_id != user.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Roteiro não encontrado")
    if r.paciente_id is not None:
        await carregar_paciente(session, user, r.paciente_id)  # escopo por profissional
    return _to_out(r)


@router.patch("/roteiros/{roteiro_id}", response_model=RoteiroOut)
async def editar_roteiro(
    roteiro_id: str,
    body: RoteiroSalvarIn,
    request: Request,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> RoteiroOut:
    try:
        rid = uuid.UUID(roteiro_id)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "id inválido")
    r = await session.get(RoteiroSessao, rid)
    if not r or r.tenant_id != user.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Roteiro não encontrado")
    if r.paciente_id is not None:
        await carregar_paciente(session, user, r.paciente_id)  # escopo por profissional

    if body.texto is not None:
        r.texto = body.texto

    if body.sessao_id is not None:
        if body.sessao_id == "":
            r.sessao_id = None
        else:
            try:
                sid = uuid.UUID(body.sessao_id)
            except ValueError:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "sessao_id inválido")
            s = await session.get(Sessao, sid)
            if not s or s.tenant_id != user.tenant_id or s.paciente_id != r.paciente_id:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Sessão não encontrada para esse paciente")
            r.sessao_id = sid

    ip = request.client.host if request.client else None
    _log(session, tenant_id=user.tenant_id, user_id=user.id, ip=ip,
         acao="ROTEIRO_EDITADO", entidade="RoteiroSessao", entidade_id=str(r.id),
         meta={"vinculou_sessao": r.sessao_id is not None})
    await session.commit()
    await session.refresh(r)
    return _to_out(r)
