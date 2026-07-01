"""Rotas dos instrumentos digitais (Maastricht, WRAP …) e anexos ao prontuário."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select

from app.deps import SessionDep, get_current_user
from app.instrumentos.geradores import formular_maastricht, planejar_wrap, redigir_leitura_escala
from app.instrumentos.pdf import render_instrumento_pdf
from app.models.audit import AuditLog
from app.models.consentimento import Consentimento
from app.models.instrumentos import AnexoProntuario, Instrumento, RespostaInstrumento
from app.models.paciente import Paciente
from app.models.user import User
from app.instrumentos.scoring import pontuar_likert
from app.schemas.instrumentos import (
    AnexoOut,
    GerarSaidaOut,
    IniciarIn,
    InstrumentoOut,
    PontuacaoOut,
    RespostaOut,
    RespostaSalvarIn,
)
from app.security.crypto import decrypt_bytes, decrypt_str, encrypt_bytes

router = APIRouter(tags=["instrumentos"])


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


async def _get_instrumento_por_tipo(session, tipo: str) -> Instrumento:
    instr = await session.scalar(select(Instrumento).where(Instrumento.tipo == tipo))
    if instr is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Instrumento '{tipo}' não catalogado")
    return instr


async def _get_paciente(session, user: User, paciente_id: str) -> Paciente:
    try:
        pid = uuid.UUID(paciente_id)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "paciente_id inválido")
    pac = await session.get(Paciente, pid)
    if not pac or pac.tenant_id != user.tenant_id or pac.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Paciente não encontrado")
    return pac


async def _get_resposta(session, user: User, resposta_id: str) -> RespostaInstrumento:
    try:
        rid = uuid.UUID(resposta_id)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "id inválido")
    r = await session.get(RespostaInstrumento, rid)
    if not r or r.tenant_id != user.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Resposta não encontrada")
    return r


async def _validar_consentimento_tratamento(session, tenant_id, paciente_id) -> None:
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
            "Registre o consentimento antes de gerar saídas por IA.",
        )


def _log(session, *, tenant_id, user_id, ip, acao, entidade, entidade_id, meta=None):
    session.add(AuditLog(
        tenant_id=tenant_id, user_id=user_id, ip=ip,
        acao=acao, entidade=entidade, entidade_id=entidade_id, meta=meta or {},
    ))


async def _resposta_out(session, r: RespostaInstrumento) -> RespostaOut:
    instr = await session.get(Instrumento, r.instrumento_id)
    # anexo relacionado, se houver
    anexo = await session.scalar(
        select(AnexoProntuario).where(
            AnexoProntuario.origem_tipo == "resposta_instrumento",
            AnexoProntuario.origem_id == r.id,
        )
    )
    # Escore determinístico (factual) para instrumentos likert_sum — calculado
    # sempre, na serialização, independente de `gerar-saida`.
    pontuacao = None
    if instr and (instr.definicao or {}).get("kind") == "likert_sum":
        pontuacao = PontuacaoOut(**pontuar_likert(instr.definicao, r.respostas or {}))

    return RespostaOut(
        id=str(r.id), paciente_id=str(r.paciente_id),
        instrumento_tipo=instr.tipo if instr else "",
        instrumento_versao=instr.versao if instr else "",
        status=r.status, respostas=r.respostas or {},
        saida_texto=r.saida_texto, saida_gerada_em=r.saida_gerada_em,
        saida_provider=r.saida_provider, finalizado_em=r.finalizado_em,
        anexo_id=str(anexo.id) if anexo else None,
        pontuacao=pontuacao,
        criado_em=r.criado_em, atualizado_em=r.atualizado_em,
    )


# --------------------------------------------------------------------------
# Catálogo
# --------------------------------------------------------------------------

@router.get("/instrumentos", response_model=list[InstrumentoOut])
async def listar_instrumentos(
    session: SessionDep,
    _user: Annotated[User, Depends(get_current_user)],
) -> list[InstrumentoOut]:
    rows = list((await session.scalars(select(Instrumento).order_by(Instrumento.titulo))).all())
    return [
        InstrumentoOut(id=str(r.id), tipo=r.tipo, versao=r.versao, titulo=r.titulo,
                       descricao=r.descricao, fonte=r.fonte)
        for r in rows
    ]


@router.get("/instrumentos/{tipo}", response_model=InstrumentoOut)
async def obter_instrumento(
    tipo: str,
    session: SessionDep,
    _user: Annotated[User, Depends(get_current_user)],
) -> InstrumentoOut:
    r = await _get_instrumento_por_tipo(session, tipo)
    return InstrumentoOut(id=str(r.id), tipo=r.tipo, versao=r.versao, titulo=r.titulo,
                          descricao=r.descricao, fonte=r.fonte, definicao=r.definicao)


# --------------------------------------------------------------------------
# Respostas (fluxo de preenchimento)
# --------------------------------------------------------------------------

@router.post("/pacientes/{paciente_id}/respostas-instrumento",
             response_model=RespostaOut, status_code=status.HTTP_201_CREATED)
async def iniciar(
    paciente_id: str,
    body: IniciarIn,
    request: Request,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> RespostaOut:
    pac = await _get_paciente(session, user, paciente_id)
    instr = await _get_instrumento_por_tipo(session, body.tipo)
    r = RespostaInstrumento(
        tenant_id=user.tenant_id, paciente_id=pac.id, instrumento_id=instr.id,
        autor_id=user.id, status="em_andamento", respostas={},
    )
    session.add(r)
    await session.flush()
    _log(session, tenant_id=user.tenant_id, user_id=user.id,
         ip=request.client.host if request.client else None,
         acao="INSTRUMENTO_INICIADO", entidade="RespostaInstrumento", entidade_id=str(r.id),
         meta={"tipo": instr.tipo, "versao": instr.versao})
    await session.commit()
    await session.refresh(r)
    return await _resposta_out(session, r)


@router.get("/respostas-instrumento/{resposta_id}", response_model=RespostaOut)
async def obter(
    resposta_id: str,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> RespostaOut:
    r = await _get_resposta(session, user, resposta_id)
    return await _resposta_out(session, r)


@router.get("/pacientes/{paciente_id}/respostas-instrumento", response_model=list[RespostaOut])
async def listar_por_paciente(
    paciente_id: str,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> list[RespostaOut]:
    pac = await _get_paciente(session, user, paciente_id)
    rows = list((await session.scalars(
        select(RespostaInstrumento).where(
            RespostaInstrumento.tenant_id == user.tenant_id,
            RespostaInstrumento.paciente_id == pac.id,
        ).order_by(RespostaInstrumento.criado_em.desc())
    )).all())
    return [await _resposta_out(session, r) for r in rows]


@router.patch("/respostas-instrumento/{resposta_id}", response_model=RespostaOut)
async def salvar(
    resposta_id: str,
    body: RespostaSalvarIn,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> RespostaOut:
    r = await _get_resposta(session, user, resposta_id)
    if r.status == "finalizado":
        raise HTTPException(status.HTTP_409_CONFLICT, "Já finalizado — imutável")
    if body.respostas is not None:
        # merge shallow para permitir salvamento por seção
        merged = dict(r.respostas or {})
        for sec_id, sec_val in body.respostas.items():
            if isinstance(sec_val, dict):
                cur = dict(merged.get(sec_id) or {})
                cur.update(sec_val)
                merged[sec_id] = cur
            else:
                merged[sec_id] = sec_val
        r.respostas = merged
    if body.saida_texto is not None:
        r.saida_texto = body.saida_texto
    await session.commit()
    await session.refresh(r)
    return await _resposta_out(session, r)


# --------------------------------------------------------------------------
# Gerar saída via IA
# --------------------------------------------------------------------------

@router.post("/respostas-instrumento/{resposta_id}/gerar-saida", response_model=GerarSaidaOut)
async def gerar_saida(
    resposta_id: str,
    request: Request,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> GerarSaidaOut:
    r = await _get_resposta(session, user, resposta_id)
    if r.status == "finalizado":
        raise HTTPException(status.HTTP_409_CONFLICT, "Já finalizado")

    await _validar_consentimento_tratamento(session, user.tenant_id, r.paciente_id)

    instr = await session.get(Instrumento, r.instrumento_id)
    if instr is None:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Definição do instrumento não encontrada")

    if instr.tipo == "maastricht":
        gerada = await formular_maastricht(session, instr.definicao, r.respostas or {}, user.abordagem)
    elif instr.tipo == "wrap":
        gerada = await planejar_wrap(instr.definicao, r.respostas or {})
    elif (instr.definicao or {}).get("kind") == "likert_sum":
        # Escore/faixa são calculados de forma determinística; a IA só redige a
        # leitura sobre o número pronto (nunca recalcula).
        pont = pontuar_likert(instr.definicao, r.respostas or {})
        gerada = await redigir_leitura_escala(instr.titulo, instr.definicao, pont, r.respostas or {})
    else:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Gerador não implementado para '{instr.tipo}'")

    r.saida_texto = gerada.texto
    r.saida_gerada_em = datetime.now(tz=timezone.utc)
    r.saida_provider = gerada.provider_id
    _log(session, tenant_id=user.tenant_id, user_id=user.id,
         ip=request.client.host if request.client else None,
         acao="INSTRUMENTO_SAIDA_GERADA", entidade="RespostaInstrumento", entidade_id=str(r.id),
         meta={"tipo": instr.tipo, "provider": gerada.provider_id, "chunks_acervo": len(gerada.hits)})
    await session.commit()
    await session.refresh(r)
    return GerarSaidaOut(resposta_id=str(r.id), saida_texto=r.saida_texto or "", provider=gerada.provider_id)


# --------------------------------------------------------------------------
# Finalizar → PDF anexado
# --------------------------------------------------------------------------

@router.post("/respostas-instrumento/{resposta_id}/finalizar", response_model=AnexoOut,
             status_code=status.HTTP_201_CREATED)
async def finalizar(
    resposta_id: str,
    request: Request,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> AnexoOut:
    r = await _get_resposta(session, user, resposta_id)
    if r.status == "finalizado":
        raise HTTPException(status.HTTP_409_CONFLICT, "Já finalizado")
    if not (r.saida_texto or "").strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Gere ou escreva a saída antes de finalizar")

    instr = await session.get(Instrumento, r.instrumento_id)
    pac = await session.get(Paciente, r.paciente_id)
    if instr is None or pac is None:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Contexto inconsistente")

    paciente_nome = decrypt_str(pac.nome_cifrado) or "(sem nome)"
    pdf_bytes, sha = render_instrumento_pdf(
        instrumento_titulo=instr.titulo,
        instrumento_fonte=instr.fonte,
        paciente_nome=paciente_nome,
        profissional_nome=user.nome,
        profissional_crp=user.crp,
        definicao=instr.definicao,
        respostas=r.respostas or {},
        saida_texto=r.saida_texto or "",
    )

    anexo = AnexoProntuario(
        tenant_id=user.tenant_id, paciente_id=pac.id,
        origem_tipo="resposta_instrumento", origem_id=r.id,
        titulo=f"{instr.titulo} — {paciente_nome}",
        mimetype="application/pdf",
        bytes=len(pdf_bytes), sha256=sha,
        arquivo_cifrado=encrypt_bytes(pdf_bytes),
        criado_por=user.id,
    )
    session.add(anexo)

    r.status = "finalizado"
    r.finalizado_em = datetime.now(tz=timezone.utc)

    ip = request.client.host if request.client else None
    _log(session, tenant_id=user.tenant_id, user_id=user.id, ip=ip,
         acao="INSTRUMENTO_FINALIZADO", entidade="RespostaInstrumento", entidade_id=str(r.id),
         meta={"tipo": instr.tipo, "anexo_bytes": len(pdf_bytes)})
    await session.flush()
    _log(session, tenant_id=user.tenant_id, user_id=user.id, ip=ip,
         acao="ANEXO_CRIADO", entidade="AnexoProntuario", entidade_id=str(anexo.id),
         meta={"sha256": sha, "bytes": len(pdf_bytes), "origem_tipo": "resposta_instrumento"})
    await session.commit()
    await session.refresh(anexo)

    return AnexoOut(
        id=str(anexo.id), paciente_id=str(anexo.paciente_id),
        origem_tipo=anexo.origem_tipo, origem_id=str(anexo.origem_id) if anexo.origem_id else None,
        titulo=anexo.titulo, mimetype=anexo.mimetype, bytes=anexo.bytes,
        sha256=anexo.sha256, criado_em=anexo.criado_em,
    )


# --------------------------------------------------------------------------
# Anexos
# --------------------------------------------------------------------------

@router.get("/pacientes/{paciente_id}/anexos", response_model=list[AnexoOut])
async def listar_anexos(
    paciente_id: str,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> list[AnexoOut]:
    pac = await _get_paciente(session, user, paciente_id)
    rows = list((await session.scalars(
        select(AnexoProntuario).where(
            AnexoProntuario.tenant_id == user.tenant_id,
            AnexoProntuario.paciente_id == pac.id,
        ).order_by(AnexoProntuario.criado_em.desc())
    )).all())
    return [
        AnexoOut(
            id=str(a.id), paciente_id=str(a.paciente_id),
            origem_tipo=a.origem_tipo, origem_id=str(a.origem_id) if a.origem_id else None,
            titulo=a.titulo, mimetype=a.mimetype, bytes=a.bytes,
            sha256=a.sha256, criado_em=a.criado_em,
        ) for a in rows
    ]


@router.get("/anexos/{anexo_id}/arquivo")
async def baixar_anexo(
    anexo_id: str,
    request: Request,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> Response:
    try:
        aid = uuid.UUID(anexo_id)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "id inválido")
    a = await session.get(AnexoProntuario, aid)
    if not a or a.tenant_id != user.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Anexo não encontrado")

    pdf_bytes = decrypt_bytes(a.arquivo_cifrado) or b""

    _log(session, tenant_id=user.tenant_id, user_id=user.id,
         ip=request.client.host if request.client else None,
         acao="ANEXO_BAIXADO", entidade="AnexoProntuario", entidade_id=str(a.id),
         meta={"sha256": a.sha256, "bytes": a.bytes})
    await session.commit()

    # Content-Disposition precisa ser latin-1 puro; usamos RFC 5987 (filename*)
    # para preservar acentos/em-dash no título.
    import re
    from urllib.parse import quote
    ascii_name = re.sub(r"[^A-Za-z0-9._-]+", "-", a.titulo).strip("-") or "anexo"
    utf8_name = quote(f"{a.titulo}.pdf")
    disposition = (
        f'inline; filename="{ascii_name}.pdf"; '
        f"filename*=UTF-8''{utf8_name}"
    )
    return Response(
        content=pdf_bytes,
        media_type=a.mimetype,
        headers={"Content-Disposition": disposition},
    )
