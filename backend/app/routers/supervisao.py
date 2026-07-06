"""Router de Supervisão / Estudo de Caso — apoio formativo, não conduta."""
from __future__ import annotations

import hashlib
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import desc, select

from app.authz import carregar_paciente
from app.deps import SessionDep, get_current_user
from app.models.audit import AuditLog
from app.models.consentimento import Consentimento
from app.models.paciente import Paciente
from app.models.supervisao import EstudoSupervisao
from app.models.user import User
from app.preparacao.contexto import montar_contexto_anonimo
from app.rag.retriever import Hit
from app.schemas.supervisao import (
    AnalisarIn,
    CitacaoOut,
    EstudoOut,
    EstudoResumoOut,
    EstudoSalvarIn,
)
from app.supervisao.analisador import analisar

router = APIRouter(prefix="/supervisao", tags=["supervisao"])


SNIPPET_TERCEIRO = 180
SNIPPET_PROPRIO = 300


def _snippet(h: Hit) -> str:
    limit = SNIPPET_TERCEIRO if h.is_terceiro else SNIPPET_PROPRIO
    t = h.texto.strip().replace("\n", " ")
    return (t[:limit] + "…") if len(t) > limit else t


def _hits_to_dicts(hits: list[Hit]) -> list[dict]:
    return [
        {
            "n": i, "documento_id": h.documento_id, "slug": h.slug,
            "titulo": h.titulo, "autor": h.autor, "editora": h.editora,
            "is_terceiro": h.is_terceiro,
            "capitulo": h.capitulo,
            "pagina_inicio": h.pagina_inicio, "pagina_fim": h.pagina_fim,
            "snippet": _snippet(h), "similaridade": round(h.similaridade, 3),
        }
        for i, h in enumerate(hits, start=1)
    ]


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


def _to_out(e: EstudoSupervisao) -> EstudoOut:
    return EstudoOut(
        id=str(e.id), tenant_id=str(e.tenant_id), autor_id=str(e.autor_id),
        origem=e.origem,
        paciente_id=str(e.paciente_id) if e.paciente_id else None,
        caso_hash=e.caso_hash,
        texto_analise=e.texto_analise,
        citacoes=_citacoes_from_json(e.citacoes or []),
        provider=e.provider, meta=e.meta or {},
        criado_em=e.criado_em, atualizado_em=e.atualizado_em,
    )


async def _get_estudo(session, user: User, eid: str) -> EstudoSupervisao:
    try:
        u = uuid.UUID(eid)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "id inválido")
    e = await session.get(EstudoSupervisao, u)
    if not e or e.tenant_id != user.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Estudo não encontrado")
    if e.paciente_id is not None:
        await carregar_paciente(session, user, e.paciente_id)  # escopo por profissional
    return e


async def _get_paciente(session, user: User, paciente_id: str) -> Paciente:
    # Escopo por profissional (P1): owner vê todos; profissional só os seus.
    return await carregar_paciente(session, user, paciente_id)


async def _valida_consentimento(session, tenant_id, paciente_id) -> None:
    cons = await session.scalar(
        select(Consentimento).where(
            Consentimento.tenant_id == tenant_id,
            Consentimento.paciente_id == paciente_id,
            Consentimento.tipo == "tratamento_dados",
        )
    )
    if cons is None:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Sem consentimento LGPD 'tratamento_dados' registrado para este paciente. "
            "Registre o consentimento antes de gerar estudo de caso baseado no prontuário.",
        )


def _log(session, *, tenant_id, user_id, ip, acao, entidade, entidade_id, meta=None):
    session.add(AuditLog(
        tenant_id=tenant_id, user_id=user_id, ip=ip,
        acao=acao, entidade=entidade, entidade_id=entidade_id, meta=meta or {},
    ))


# --------------------------------------------------------------------------
# Rotas
# --------------------------------------------------------------------------

@router.post("/analisar", response_model=EstudoOut, status_code=status.HTTP_201_CREATED)
async def analisar_endpoint(
    body: AnalisarIn,
    request: Request,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> EstudoOut:
    ip = request.client.host if request.client else None

    if body.paciente_id:
        # Modo paciente do prontuário.
        pac = await _get_paciente(session, user, body.paciente_id)
        await _valida_consentimento(session, user.tenant_id, pac.id)
        ctx = await montar_contexto_anonimo(session, pac)
        descricao_caso = (
            "O caso está descrito no retrato clínico anonimizado abaixo, "
            "extraído do prontuário do paciente."
        )
        analise = await analisar(
            session, descricao_caso=descricao_caso,
            ctx_paciente=ctx, abordagem_prof=user.abordagem,
        )
        origem = "paciente"
        paciente_uuid = pac.id
        caso_hash = None
        audit_meta = {
            "origem": origem,
            "provider": analise.provider_id,
            "n_evolucoes": ctx.n_evolucoes_assinadas,
            "n_instrumentos": ctx.n_instrumentos_finalizados,
            "n_chunks_acervo": len(analise.hits),
            "abordagens": analise.meta.get("abordagens_comparadas"),
        }
    else:
        # Modo avulso — NÃO persistimos o texto do caso, só a análise.
        assert body.caso_texto is not None  # garantido pelo validator
        analise = await analisar(
            session, descricao_caso=body.caso_texto,
            ctx_paciente=None, abordagem_prof=user.abordagem,
        )
        origem = "avulso"
        paciente_uuid = None
        caso_hash = hashlib.sha256(body.caso_texto.encode("utf-8")).hexdigest()
        audit_meta = {
            "origem": origem,
            "provider": analise.provider_id,
            "caso_hash": caso_hash,
            "caso_chars": len(body.caso_texto),
            "n_chunks_acervo": len(analise.hits),
            "abordagens": analise.meta.get("abordagens_comparadas"),
        }

    e = EstudoSupervisao(
        tenant_id=user.tenant_id, autor_id=user.id,
        origem=origem, paciente_id=paciente_uuid, caso_hash=caso_hash,
        texto_analise=analise.texto,
        citacoes=_hits_to_dicts(analise.hits),
        provider=analise.provider_id,
        meta=analise.meta,
    )
    session.add(e)
    await session.flush()

    _log(session, tenant_id=user.tenant_id, user_id=user.id, ip=ip,
         acao="SUPERVISAO_ANALISE_GERADA", entidade="EstudoSupervisao",
         entidade_id=str(e.id), meta=audit_meta)
    await session.commit()
    await session.refresh(e)
    return _to_out(e)


@router.get("/estudos", response_model=list[EstudoResumoOut])
async def listar(
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> list[EstudoResumoOut]:
    rows = list((await session.scalars(
        select(EstudoSupervisao)
        .where(EstudoSupervisao.tenant_id == user.tenant_id,
               EstudoSupervisao.autor_id == user.id)
        .order_by(desc(EstudoSupervisao.criado_em))
        .limit(30)
    )).all())
    return [
        EstudoResumoOut(
            id=str(r.id), origem=r.origem,
            paciente_id=str(r.paciente_id) if r.paciente_id else None,
            preview=(r.texto_analise or "").strip().split("\n")[0][:180],
            provider=r.provider,
            criado_em=r.criado_em, atualizado_em=r.atualizado_em,
        )
        for r in rows
    ]


@router.get("/estudos/{estudo_id}", response_model=EstudoOut)
async def obter(
    estudo_id: str,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> EstudoOut:
    e = await _get_estudo(session, user, estudo_id)
    return _to_out(e)


@router.patch("/estudos/{estudo_id}", response_model=EstudoOut)
async def editar(
    estudo_id: str,
    body: EstudoSalvarIn,
    request: Request,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> EstudoOut:
    e = await _get_estudo(session, user, estudo_id)
    if body.texto_analise is not None:
        e.texto_analise = body.texto_analise
    ip = request.client.host if request.client else None
    _log(session, tenant_id=user.tenant_id, user_id=user.id, ip=ip,
         acao="SUPERVISAO_EDITADA", entidade="EstudoSupervisao",
         entidade_id=str(e.id), meta={})
    await session.commit()
    await session.refresh(e)
    return _to_out(e)


@router.delete("/estudos/{estudo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remover(
    estudo_id: str,
    request: Request,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> None:
    e = await _get_estudo(session, user, estudo_id)
    if e.autor_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Só o autor pode remover")
    eid = str(e.id)
    origem = e.origem
    ip = request.client.host if request.client else None
    _log(session, tenant_id=user.tenant_id, user_id=user.id, ip=ip,
         acao="SUPERVISAO_REMOVIDA", entidade="EstudoSupervisao",
         entidade_id=eid, meta={"origem": origem})
    await session.delete(e)
    await session.commit()
