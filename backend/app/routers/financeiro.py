"""Financeiro & Recibos — valor por sessão, controle de pagamento e recibo PDF.

Factual: pendências são derivadas das sessões realizadas com valor (não há
linha `pendente` persistida); só gravamos `pagamentos` ao marcar pago. Valores
sempre em centavos (inteiro). Tenant-scoped. Recibo ≠ NF-e.
"""
from __future__ import annotations

import re
import uuid
from datetime import date, datetime, timezone
from typing import Annotated, Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import func, select, text

from app.deps import SessionDep, get_current_user
from app.financeiro.recibo_pdf import render_recibo_pdf
from app.models.audit import AuditLog
from app.models.financeiro import Pagamento, Recibo
from app.models.instrumentos import AnexoProntuario
from app.models.paciente import Paciente
from app.models.sessao import Sessao
from app.models.user import User
from app.schemas.financeiro import (
    LancamentoOut,
    PagamentoOut,
    PagarIn,
    ReciboIn,
    ReciboOut,
    ReciboRefOut,
)
from app.security.crypto import decrypt_bytes, decrypt_str, encrypt_bytes

router = APIRouter(prefix="/financeiro", tags=["financeiro"])


def _log(session, *, tenant_id, user_id, ip, acao, entidade, entidade_id, meta=None):
    session.add(AuditLog(
        tenant_id=tenant_id, user_id=user_id, ip=ip,
        acao=acao, entidade=entidade, entidade_id=entidade_id, meta=meta or {},
    ))


async def _get_sessao(session, user: User, sessao_id: str) -> Sessao:
    try:
        sid = uuid.UUID(sessao_id)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "sessao_id inválido")
    s = await session.get(Sessao, sid)
    if not s or s.tenant_id != user.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sessão não encontrada")
    return s


# --------------------------------------------------------------------------
# Pagamentos (lançamentos) — sessões realizadas com valor, status derivado
# --------------------------------------------------------------------------

@router.get("/pagamentos", response_model=list[LancamentoOut])
async def listar_pagamentos(
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
    status_filtro: Annotated[Literal["pendente", "pago"] | None, Query(alias="status")] = None,
    de: date | None = None,
    ate: date | None = None,
) -> list[LancamentoOut]:
    q = (
        select(Sessao, Paciente.nome_cifrado, Pagamento, Recibo)
        .join(Paciente, Paciente.id == Sessao.paciente_id)
        .join(Pagamento, Pagamento.sessao_id == Sessao.id, isouter=True)
        .join(Recibo, Recibo.sessao_id == Sessao.id, isouter=True)
        .where(
            Sessao.tenant_id == user.tenant_id,
            Sessao.status == "realizada",
            Sessao.valor_centavos.isnot(None),
            Paciente.deleted_at.is_(None),
        )
        .order_by(Sessao.data.desc())
    )
    if de is not None:
        q = q.where(func.date(Sessao.data) >= de)
    if ate is not None:
        q = q.where(func.date(Sessao.data) <= ate)

    out: list[LancamentoOut] = []
    for s, nome_cifrado, pag, rec in (await session.execute(q)).all():
        st = "pago" if (pag is not None and pag.status == "pago") else "pendente"
        if status_filtro is not None and st != status_filtro:
            continue
        out.append(LancamentoOut(
            sessao_id=str(s.id),
            paciente_id=str(s.paciente_id),
            paciente_nome=decrypt_str(nome_cifrado) or "—",
            data=s.data,
            valor_centavos=s.valor_centavos,
            status=st,
            forma=pag.forma if pag else None,
            pago_em=pag.pago_em if pag else None,
            recibo=ReciboRefOut(id=str(rec.id), numero=rec.numero) if rec else None,
        ))
    return out


@router.post("/pagamentos/{sessao_id}", response_model=PagamentoOut, status_code=status.HTTP_201_CREATED)
async def registrar_pagamento(
    sessao_id: str,
    body: PagarIn,
    request: Request,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> PagamentoOut:
    s = await _get_sessao(session, user, sessao_id)
    if s.valor_centavos is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Sessão sem valor definido")

    existente = await session.scalar(select(Pagamento).where(Pagamento.sessao_id == s.id))
    if existente is not None and existente.status == "pago":
        raise HTTPException(status.HTTP_409_CONFLICT, "Sessão já está paga")

    pago_em = body.pago_em or datetime.now(tz=timezone.utc)
    pag = existente or Pagamento(
        tenant_id=user.tenant_id, sessao_id=s.id,
        valor_centavos=s.valor_centavos, criado_por=user.id,
    )
    pag.valor_centavos = s.valor_centavos  # snapshot factual do valor no ato
    pag.status = "pago"
    pag.forma = body.forma
    pag.pago_em = pago_em
    if existente is None:
        session.add(pag)

    _log(session, tenant_id=user.tenant_id, user_id=user.id,
         ip=request.client.host if request.client else None,
         acao="PAGAMENTO_REGISTRADO", entidade="Pagamento", entidade_id=str(s.id),
         meta={"valor_centavos": s.valor_centavos, "forma": body.forma})
    await session.commit()
    await session.refresh(pag)
    return PagamentoOut(
        id=str(pag.id), sessao_id=str(pag.sessao_id), valor_centavos=pag.valor_centavos,
        status=pag.status, forma=pag.forma, pago_em=pag.pago_em,
        recibo_id=str(pag.recibo_id) if pag.recibo_id else None,
    )


# --------------------------------------------------------------------------
# Recibos
# --------------------------------------------------------------------------

async def _proximo_numero(session, tenant_id: uuid.UUID) -> int:
    """Numeração sequencial atômica por tenant (upsert RETURNING, sem race)."""
    numero = await session.scalar(
        text(
            """
            INSERT INTO recibo_contadores (tenant_id, proximo) VALUES (:t, 1)
            ON CONFLICT (tenant_id)
            DO UPDATE SET proximo = recibo_contadores.proximo + 1
            RETURNING proximo
            """
        ),
        {"t": str(tenant_id)},
    )
    return int(numero)


def _pdf_response(pdf_bytes: bytes, titulo: str, numero: int) -> Response:
    ascii_name = re.sub(r"[^A-Za-z0-9._-]+", "-", titulo).strip("-") or "recibo"
    utf8_name = quote(f"{titulo}.pdf")
    disposition = f'inline; filename="{ascii_name}.pdf"; filename*=UTF-8\'\'{utf8_name}'
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": disposition, "X-Recibo-Numero": str(numero)},
    )


@router.post("/recibos")
async def emitir_recibo(
    body: ReciboIn,
    request: Request,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> Response:
    s = await _get_sessao(session, user, body.sessao_id)

    # Só se emite recibo de valor recebido.
    pag = await session.scalar(select(Pagamento).where(Pagamento.sessao_id == s.id))
    if pag is None or pag.status != "pago":
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            "Marque a sessão como paga antes de emitir o recibo")

    pac = await session.get(Paciente, s.paciente_id)
    if pac is None or pac.tenant_id != user.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Paciente não encontrado")
    pac_nome = decrypt_str(pac.nome_cifrado) or "(sem nome)"

    # 1 recibo por sessão: reemissão devolve o existente (não queima número).
    existente = await session.scalar(select(Recibo).where(Recibo.sessao_id == s.id))
    if existente is not None:
        if existente.anexo_id is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Recibo sem PDF anexado")
        anexo = await session.get(AnexoProntuario, existente.anexo_id)
        pdf_bytes = decrypt_bytes(anexo.arquivo_cifrado) or b""
        return _pdf_response(pdf_bytes, f"Recibo {existente.numero:04d} — {pac_nome}", existente.numero)

    numero = await _proximo_numero(session, user.tenant_id)
    emitido_em = datetime.now(tz=timezone.utc)
    pac_cpf = decrypt_str(pac.documento_cifrado)

    pdf_bytes, sha_pdf = render_recibo_pdf(
        numero=numero, paciente_nome=pac_nome, paciente_cpf=pac_cpf,
        profissional_nome=user.nome, profissional_crp=user.crp,
        valor_centavos=pag.valor_centavos, data_sessao=s.data, emitido_em=emitido_em,
    )

    anexo = AnexoProntuario(
        tenant_id=user.tenant_id, paciente_id=pac.id,
        origem_tipo="recibo", origem_id=None,
        titulo=f"Recibo nº {numero:04d} — {pac_nome} — {emitido_em.strftime('%d/%m/%Y')}",
        mimetype="application/pdf", bytes=len(pdf_bytes), sha256=sha_pdf,
        arquivo_cifrado=encrypt_bytes(pdf_bytes), criado_por=user.id,
    )
    session.add(anexo)
    await session.flush()

    rec = Recibo(
        tenant_id=user.tenant_id, numero=numero, paciente_id=pac.id, sessao_id=s.id,
        valor_centavos=pag.valor_centavos, emitido_por=user.id,
        emitido_em=emitido_em, anexo_id=anexo.id,
    )
    session.add(rec)
    await session.flush()
    anexo.origem_id = rec.id
    pag.recibo_id = rec.id

    ip = request.client.host if request.client else None
    _log(session, tenant_id=user.tenant_id, user_id=user.id, ip=ip,
         acao="RECIBO_EMITIDO", entidade="Recibo", entidade_id=str(rec.id),
         meta={"numero": numero, "valor_centavos": pag.valor_centavos, "sessao_id": str(s.id)})
    _log(session, tenant_id=user.tenant_id, user_id=user.id, ip=ip,
         acao="ANEXO_CRIADO", entidade="AnexoProntuario", entidade_id=str(anexo.id),
         meta={"sha256": sha_pdf, "bytes": len(pdf_bytes), "origem_tipo": "recibo"})
    await session.commit()

    return _pdf_response(pdf_bytes, f"Recibo {numero:04d} — {pac_nome}", numero)


@router.get("/recibos", response_model=list[ReciboOut])
async def listar_recibos(
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
    de: date | None = None,
    ate: date | None = None,
) -> list[ReciboOut]:
    q = (
        select(Recibo, Paciente.nome_cifrado)
        .join(Paciente, Paciente.id == Recibo.paciente_id)
        .where(Recibo.tenant_id == user.tenant_id)
        .order_by(Recibo.numero.desc())
    )
    if de is not None:
        q = q.where(func.date(Recibo.emitido_em) >= de)
    if ate is not None:
        q = q.where(func.date(Recibo.emitido_em) <= ate)
    return [
        ReciboOut(
            id=str(r.id), numero=r.numero, paciente_id=str(r.paciente_id),
            paciente_nome=decrypt_str(nome_cifrado) or "—",
            valor_centavos=r.valor_centavos, emitido_em=r.emitido_em,
            anexo_id=str(r.anexo_id) if r.anexo_id else None,
        )
        for r, nome_cifrado in (await session.execute(q)).all()
    ]


@router.get("/recibos/{recibo_id}")
async def baixar_recibo(
    recibo_id: str,
    request: Request,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> Response:
    try:
        rid = uuid.UUID(recibo_id)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "id inválido")
    rec = await session.get(Recibo, rid)
    if not rec or rec.tenant_id != user.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recibo não encontrado")
    if rec.anexo_id is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recibo sem PDF anexado")
    anexo = await session.get(AnexoProntuario, rec.anexo_id)
    pdf_bytes = decrypt_bytes(anexo.arquivo_cifrado) or b""

    _log(session, tenant_id=user.tenant_id, user_id=user.id,
         ip=request.client.host if request.client else None,
         acao="RECIBO_BAIXADO", entidade="Recibo", entidade_id=str(rec.id),
         meta={"numero": rec.numero})
    await session.commit()
    return _pdf_response(pdf_bytes, f"Recibo {rec.numero:04d}", rec.numero)
