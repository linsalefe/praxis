"""Casos e PTS (espinha Caso/PTS, Onda 1.2).

`Caso` agrega o cuidado de um paciente; `PtsVersao` é o Projeto Terapêutico
Singular versionado (cada save = nova versão; a atual é a de maior número).

Escopo tenant + sigilo por profissional: o acesso ao caso é validado pelo acesso
ao paciente dono (`carregar_paciente`), então owner vê todos e profissional só os
seus. Aditivo: o consultório pode ignorar casos; nada quebra sem eles.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select

from app.authz import acessa_prontuario, carregar_paciente, is_owner, pode_acessar_paciente
from app.casos.pts import PTS_SECAO_IDS, definicao
from app.deps import SessionDep, get_current_user
from app.models.audit import AuditLog
from app.models.caso import Caso, PtsVersao
from app.models.matriciamento import Matriciamento
from app.models.paciente import Paciente
from app.models.rede import MembroRede
from app.models.user import User
from app.schemas.caso import (
    CasoCompartilhadoOut,
    CasoCreate,
    CasoOut,
    CasoResumo,
    CasoUpdate,
    MatriciamentoCreate,
    MatriciamentoOut,
    MembroRedeCreate,
    MembroRedeOut,
    MembroRedeUpdate,
    PtsSalvar,
    PtsVersaoOut,
)
from app.security.crypto import decrypt_str, encrypt_str

router = APIRouter(tags=["casos"])


def _pode_compartilhar(user: User, caso: Caso) -> bool:
    """Quem pode ligar/desligar o compartilhamento: dono do caso ou owner do tenant."""
    return is_owner(user) or caso.criado_por == user.id


async def _carregar_caso(session, user: User, caso_id: str) -> Caso:
    """Carrega um caso do tenant respeitando o sigilo.

    Acesso é concedido quando (a) o usuário acessa o paciente dono do caso —
    dono do paciente ou owner do tenant (sigilo estrito, padrão) — OU (b) o caso
    está `compartilhado` e o usuário tem papel clínico (co-autoria de equipe,
    Onda 2.1). Caso contrário, 404 (não vaza existência).
    """
    try:
        cid = uuid.UUID(caso_id)
    except (ValueError, TypeError):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "caso_id inválido")
    caso = await session.get(Caso, cid)
    if caso is None or caso.tenant_id != user.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Caso não encontrado")
    pac = await session.get(Paciente, caso.paciente_id)
    if pac is None or pac.tenant_id != user.tenant_id or pac.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Caso não encontrado")
    if pode_acessar_paciente(user, pac):
        return caso  # dono do paciente ou owner — sigilo estrito
    if caso.compartilhado and acessa_prontuario(user):
        return caso  # compartilhado com a equipe
    raise HTTPException(status.HTTP_404_NOT_FOUND, "Caso não encontrado")


async def _nomes_por_id(session, ids: set[uuid.UUID]) -> dict[uuid.UUID, str]:
    """Mapa user_id -> nome, para atribuir autoria (co-autoria de equipe)."""
    ids = {i for i in ids if i is not None}
    if not ids:
        return {}
    rows = (await session.scalars(select(User).where(User.id.in_(ids)))).all()
    return {u.id: u.nome for u in rows}


async def _pts_atual(session, caso_id: uuid.UUID) -> PtsVersao | None:
    return await session.scalar(
        select(PtsVersao).where(PtsVersao.caso_id == caso_id).order_by(PtsVersao.versao.desc()).limit(1)
    )


def _pts_out(p: PtsVersao, autor_nome: str | None = None) -> PtsVersaoOut:
    return PtsVersaoOut(
        id=str(p.id), caso_id=str(p.caso_id), versao=p.versao,
        conteudo=p.conteudo or {}, criado_por=str(p.criado_por),
        autor_nome=autor_nome, criado_em=p.criado_em,
    )


def _caso_out(caso: Caso, pts: PtsVersao | None, user: User, autor_nome: str | None = None) -> CasoOut:
    return CasoOut(
        id=str(caso.id), paciente_id=str(caso.paciente_id), titulo=caso.titulo,
        status=caso.status, compartilhado=caso.compartilhado,
        pode_compartilhar=_pode_compartilhar(user, caso),
        aberto_em=caso.aberto_em, encerrado_em=caso.encerrado_em,
        criado_em=caso.criado_em,
        pts_atual=_pts_out(pts, autor_nome) if pts else None,
    )


@router.get("/casos/pts/definicao")
async def get_definicao(_user: Annotated[User, Depends(get_current_user)]) -> dict:
    """Seções do PTS (fonte única do formulário)."""
    return definicao()


@router.post(
    "/pacientes/{paciente_id}/casos",
    response_model=CasoOut,
    status_code=status.HTTP_201_CREATED,
)
async def criar_caso(
    paciente_id: str,
    body: CasoCreate,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> CasoOut:
    pac = await carregar_paciente(session, user, paciente_id)
    caso = Caso(
        tenant_id=user.tenant_id, paciente_id=pac.id, criado_por=user.id,
        titulo=(body.titulo or None),
    )
    session.add(caso)
    await session.commit()
    await session.refresh(caso)
    return _caso_out(caso, None, user)


@router.get("/pacientes/{paciente_id}/casos", response_model=list[CasoResumo])
async def listar_casos(
    paciente_id: str,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> list[CasoResumo]:
    await carregar_paciente(session, user, paciente_id)
    q = (
        select(Caso)
        .where(Caso.tenant_id == user.tenant_id, Caso.paciente_id == uuid.UUID(paciente_id))
        .order_by(Caso.aberto_em.desc())
    )
    casos = list((await session.scalars(q)).all())
    out: list[CasoResumo] = []
    for c in casos:
        vmax = await session.scalar(
            select(func.max(PtsVersao.versao)).where(PtsVersao.caso_id == c.id)
        )
        out.append(CasoResumo(
            id=str(c.id), paciente_id=str(c.paciente_id), titulo=c.titulo,
            status=c.status, compartilhado=c.compartilhado,
            aberto_em=c.aberto_em, pts_versao_atual=vmax,
        ))
    return out


# Declarado ANTES de "/casos/{caso_id}" para não ser capturado pela rota dinâmica.
@router.get("/casos/compartilhados", response_model=list[CasoCompartilhadoOut])
async def listar_compartilhados(
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> list[CasoCompartilhadoOut]:
    """Quadro de casos compartilhados com a equipe do tenant (Onda 2.1).

    A porta de entrada da equipe: um profissional que não é dono do paciente não
    chega ao caso pelo prontuário, então descobre os casos compartilhados aqui.
    """
    if not acessa_prontuario(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Sem acesso a prontuário")
    q = (
        select(Caso)
        .where(Caso.tenant_id == user.tenant_id, Caso.compartilhado.is_(True))
        .order_by(Caso.atualizado_em.desc())
    )
    casos = list((await session.scalars(q)).all())
    donos = await _nomes_por_id(session, {c.criado_por for c in casos})
    out: list[CasoCompartilhadoOut] = []
    for c in casos:
        pac = await session.get(Paciente, c.paciente_id)
        if pac is None or pac.deleted_at is not None:
            continue
        vmax = await session.scalar(
            select(func.max(PtsVersao.versao)).where(PtsVersao.caso_id == c.id)
        )
        out.append(CasoCompartilhadoOut(
            id=str(c.id), paciente_id=str(c.paciente_id),
            paciente_nome=decrypt_str(pac.nome_cifrado) or "—",
            titulo=c.titulo, status=c.status,
            dono_nome=donos.get(c.criado_por),
            aberto_em=c.aberto_em, pts_versao_atual=vmax,
        ))
    return out


@router.get("/casos/{caso_id}", response_model=CasoOut)
async def detalhe_caso(
    caso_id: str,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> CasoOut:
    caso = await _carregar_caso(session, user, caso_id)
    pts = await _pts_atual(session, caso.id)
    autor = (await _nomes_por_id(session, {pts.criado_por})).get(pts.criado_por) if pts else None
    return _caso_out(caso, pts, user, autor)


@router.patch("/casos/{caso_id}", response_model=CasoOut)
async def atualizar_caso(
    caso_id: str,
    body: CasoUpdate,
    request: Request,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> CasoOut:
    caso = await _carregar_caso(session, user, caso_id)
    if body.titulo is not None:
        caso.titulo = body.titulo or None
    if body.status is not None:
        if body.status not in ("ativo", "encerrado"):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "status inválido")
        caso.status = body.status
        caso.encerrado_em = datetime.now(timezone.utc) if body.status == "encerrado" else None
    if body.compartilhado is not None and body.compartilhado != caso.compartilhado:
        # Ligar/desligar o compartilhamento controla a exposição do caso à equipe:
        # ação sensível, restrita ao dono do caso/owner e auditada.
        if not _pode_compartilhar(user, caso):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Só o responsável pelo caso ou o owner pode alterar o compartilhamento.",
            )
        caso.compartilhado = body.compartilhado
        ip = request.client.host if request.client else None
        session.add(AuditLog(
            tenant_id=user.tenant_id, user_id=user.id, ip=ip,
            acao="CASO_COMPARTILHAR", entidade="Caso", entidade_id=str(caso.id),
            meta={"compartilhado": caso.compartilhado},
        ))
    await session.commit()
    await session.refresh(caso)
    pts = await _pts_atual(session, caso.id)
    autor = (await _nomes_por_id(session, {pts.criado_por})).get(pts.criado_por) if pts else None
    return _caso_out(caso, pts, user, autor)


@router.post("/casos/{caso_id}/pts", response_model=PtsVersaoOut, status_code=status.HTTP_201_CREATED)
async def salvar_pts(
    caso_id: str,
    body: PtsSalvar,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> PtsVersaoOut:
    """Cria uma nova versão do PTS (imutável). Só chaves de seção conhecidas."""
    caso = await _carregar_caso(session, user, caso_id)
    conteudo = {
        k: v.strip()
        for k, v in (body.conteudo or {}).items()
        if k in PTS_SECAO_IDS and v and v.strip()
    }
    vmax = await session.scalar(select(func.max(PtsVersao.versao)).where(PtsVersao.caso_id == caso.id))
    pts = PtsVersao(
        tenant_id=user.tenant_id, caso_id=caso.id, versao=(vmax or 0) + 1,
        conteudo=conteudo, criado_por=user.id,
    )
    session.add(pts)
    await session.commit()
    await session.refresh(pts)
    return _pts_out(pts, user.nome)


@router.get("/casos/{caso_id}/pts", response_model=list[PtsVersaoOut])
async def historico_pts(
    caso_id: str,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> list[PtsVersaoOut]:
    caso = await _carregar_caso(session, user, caso_id)
    q = select(PtsVersao).where(PtsVersao.caso_id == caso.id).order_by(PtsVersao.versao.desc())
    versoes = list((await session.scalars(q)).all())
    nomes = await _nomes_por_id(session, {p.criado_por for p in versoes})
    return [_pts_out(p, nomes.get(p.criado_por)) for p in versoes]


# --------------------------------------------------------------------------
# Rede de apoio (genograma/ecomapa) — Onda 2.3
# --------------------------------------------------------------------------

def _membro_out(m: MembroRede) -> MembroRedeOut:
    return MembroRedeOut(
        id=str(m.id), caso_id=str(m.caso_id), nome=decrypt_str(m.nome_cifrado) or "—",
        papel=m.papel, tipo_vinculo=m.tipo_vinculo, forca_vinculo=m.forca_vinculo,
        observacoes=m.observacoes,
    )


async def _carregar_membro(session, caso: Caso, membro_id: str) -> MembroRede:
    try:
        mid = uuid.UUID(membro_id)
    except (ValueError, TypeError):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "membro_id inválido")
    m = await session.get(MembroRede, mid)
    if m is None or m.caso_id != caso.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Membro não encontrado")
    return m


@router.get("/casos/{caso_id}/rede", response_model=list[MembroRedeOut])
async def listar_rede(
    caso_id: str,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> list[MembroRedeOut]:
    caso = await _carregar_caso(session, user, caso_id)
    q = select(MembroRede).where(MembroRede.caso_id == caso.id).order_by(MembroRede.criado_em)
    return [_membro_out(m) for m in (await session.scalars(q)).all()]


@router.post("/casos/{caso_id}/rede", response_model=MembroRedeOut, status_code=status.HTTP_201_CREATED)
async def adicionar_membro(
    caso_id: str,
    body: MembroRedeCreate,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> MembroRedeOut:
    caso = await _carregar_caso(session, user, caso_id)
    if not body.nome.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Nome é obrigatório")
    m = MembroRede(
        tenant_id=user.tenant_id, caso_id=caso.id, criado_por=user.id,
        nome_cifrado=encrypt_str(body.nome.strip()), papel=(body.papel or None),
        tipo_vinculo=body.tipo_vinculo, forca_vinculo=body.forca_vinculo,
        observacoes=(body.observacoes or None),
    )
    session.add(m)
    await session.commit()
    await session.refresh(m)
    return _membro_out(m)


@router.patch("/casos/{caso_id}/rede/{membro_id}", response_model=MembroRedeOut)
async def atualizar_membro(
    caso_id: str,
    membro_id: str,
    body: MembroRedeUpdate,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> MembroRedeOut:
    caso = await _carregar_caso(session, user, caso_id)
    m = await _carregar_membro(session, caso, membro_id)
    if body.nome is not None:
        if not body.nome.strip():
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Nome não pode ser vazio")
        m.nome_cifrado = encrypt_str(body.nome.strip())
    if body.papel is not None:
        m.papel = body.papel or None
    if body.tipo_vinculo is not None:
        m.tipo_vinculo = body.tipo_vinculo
    if body.forca_vinculo is not None:
        m.forca_vinculo = body.forca_vinculo
    if body.observacoes is not None:
        m.observacoes = body.observacoes or None
    await session.commit()
    await session.refresh(m)
    return _membro_out(m)


@router.delete("/casos/{caso_id}/rede/{membro_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remover_membro(
    caso_id: str,
    membro_id: str,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> None:
    caso = await _carregar_caso(session, user, caso_id)
    m = await _carregar_membro(session, caso, membro_id)
    await session.delete(m)
    await session.commit()


# --------------------------------------------------------------------------
# Matriciamento / apoio matricial — Onda 2.4
# --------------------------------------------------------------------------

def _matric_out(m: Matriciamento, autor_nome: str | None = None) -> MatriciamentoOut:
    return MatriciamentoOut(
        id=str(m.id), caso_id=str(m.caso_id), data=m.data,
        equipe_referencia=m.equipe_referencia, demanda=m.demanda,
        discussao=m.discussao, combinados=m.combinados,
        autor_nome=autor_nome, criado_em=m.criado_em,
    )


@router.get("/casos/{caso_id}/matriciamentos", response_model=list[MatriciamentoOut])
async def listar_matriciamentos(
    caso_id: str,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> list[MatriciamentoOut]:
    caso = await _carregar_caso(session, user, caso_id)
    q = select(Matriciamento).where(Matriciamento.caso_id == caso.id).order_by(Matriciamento.data.desc())
    registros = list((await session.scalars(q)).all())
    nomes = await _nomes_por_id(session, {m.criado_por for m in registros})
    return [_matric_out(m, nomes.get(m.criado_por)) for m in registros]


@router.post("/casos/{caso_id}/matriciamentos", response_model=MatriciamentoOut, status_code=status.HTTP_201_CREATED)
async def criar_matriciamento(
    caso_id: str,
    body: MatriciamentoCreate,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> MatriciamentoOut:
    caso = await _carregar_caso(session, user, caso_id)
    m = Matriciamento(
        tenant_id=user.tenant_id, caso_id=caso.id, criado_por=user.id,
        data=body.data or datetime.now(timezone.utc),
        equipe_referencia=(body.equipe_referencia or None), demanda=(body.demanda or None),
        discussao=(body.discussao or None), combinados=(body.combinados or None),
    )
    session.add(m)
    await session.commit()
    await session.refresh(m)
    return _matric_out(m, user.nome)


@router.delete("/casos/{caso_id}/matriciamentos/{matric_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remover_matriciamento(
    caso_id: str,
    matric_id: str,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> None:
    caso = await _carregar_caso(session, user, caso_id)
    try:
        mid = uuid.UUID(matric_id)
    except (ValueError, TypeError):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "matric_id inválido")
    m = await session.get(Matriciamento, mid)
    if m is None or m.caso_id != caso.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Matriciamento não encontrado")
    await session.delete(m)
    await session.commit()
