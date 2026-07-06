"""Router de documentos CFP (Res. 06/2019).

Fluxo:
  POST /documentos/gerar          → cria rascunho via LLM (com placeholders)
  GET  /documentos/{id}
  PATCH /documentos/{id}          → editar conteúdo/finalidade
  POST /documentos/{id}/assinar   → assina (imutável), renderiza PDF, anexa ao prontuário
  GET  /pacientes/{id}/documentos
  GET  /documentos/templates       → catálogo dos 5 tipos (com blocos)
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import desc, select

from app.authz import carregar_paciente
from app.deps import SessionDep, get_current_user
from app.documentos.gerador import gerar_documento
from app.documentos.pdf import render_documento_pdf
from app.pdftimbre import Timbre
from app.documentos.substituir import montar_valores, substituir_conteudo
from app.documentos.templates import TEMPLATES
from app.models.audit import AuditLog
from app.models.consentimento import Consentimento
from app.models.documento import DocumentoCFP
from app.assinatura.pades import assinar_pades
from app.models.certificado import CertificadoAssinatura
from app.models.instrumentos import AnexoProntuario
from app.models.paciente import Paciente
from app.models.user import User
from app.preparacao.contexto import montar_contexto_anonimo
from app.schemas.assinatura import AssinarICPIn
from app.schemas.documentos import (
    DocumentoBlocoTemplate,
    DocumentoOut,
    DocumentoSalvarIn,
    DocumentoTemplateOut,
    GerarIn,
)
from app.security.crypto import decrypt_bytes, decrypt_str, encrypt_bytes

router = APIRouter(tags=["documentos"])


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

async def _get_paciente(session, user: User, paciente_id: str) -> Paciente:
    # Escopo por profissional (P1): owner vê todos; profissional só os seus.
    return await carregar_paciente(session, user, paciente_id)


async def _get_doc(session, user: User, doc_id: str) -> DocumentoCFP:
    try:
        did = uuid.UUID(doc_id)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "id inválido")
    d = await session.get(DocumentoCFP, did)
    if not d or d.tenant_id != user.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Documento não encontrado")
    await carregar_paciente(session, user, d.paciente_id)  # escopo por profissional
    return d


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
            "Registre o consentimento antes de gerar documentos.",
        )


def _log(session, *, tenant_id, user_id, ip, acao, entidade, entidade_id, meta=None):
    session.add(AuditLog(
        tenant_id=tenant_id, user_id=user_id, ip=ip,
        acao=acao, entidade=entidade, entidade_id=entidade_id, meta=meta or {},
    ))


def _to_out(d: DocumentoCFP) -> DocumentoOut:
    return DocumentoOut(
        id=str(d.id), tenant_id=str(d.tenant_id),
        paciente_id=str(d.paciente_id), autor_id=str(d.autor_id),
        tipo=d.tipo, finalidade=d.finalidade, destinatario=d.destinatario,
        conteudo=d.conteudo or {}, status=d.status,
        provider=d.provider, prompt_versao=d.prompt_versao,
        assinado_em=d.assinado_em, hash_assinatura=d.hash_assinatura,
        anexo_pdf_id=str(d.anexo_pdf_id) if d.anexo_pdf_id else None,
        assinatura_tipo=d.assinatura_tipo, cert_titular=d.cert_titular,
        criado_em=d.criado_em, atualizado_em=d.atualizado_em,
    )


def _hash_conteudo(d: DocumentoCFP) -> str:
    payload = {
        "tenant": str(d.tenant_id),
        "paciente": str(d.paciente_id),
        "autor": str(d.autor_id),
        "tipo": d.tipo,
        "finalidade": d.finalidade,
        "destinatario": d.destinatario or "",
        "conteudo": d.conteudo or {},
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


# --------------------------------------------------------------------------
# Catálogo de templates
# --------------------------------------------------------------------------

@router.get("/documentos/templates", response_model=list[DocumentoTemplateOut])
async def listar_templates(
    _user: Annotated[User, Depends(get_current_user)],
) -> list[DocumentoTemplateOut]:
    out: list[DocumentoTemplateOut] = []
    for tipo, tpl in TEMPLATES.items():
        out.append(DocumentoTemplateOut(
            tipo=tipo,   # type: ignore[arg-type]
            titulo=tpl["titulo"],
            descricao=tpl["descricao"],
            blocos=[
                DocumentoBlocoTemplate(
                    id=b["id"], label=b["label"], hint=b["hint"],
                    palavras_alvo=(b["palavras_alvo"][0], b["palavras_alvo"][1]),
                ) for b in tpl["blocos"]
            ],
        ))
    return out


# --------------------------------------------------------------------------
# Gerar
# --------------------------------------------------------------------------

@router.post("/documentos/gerar", response_model=DocumentoOut,
             status_code=status.HTTP_201_CREATED)
async def gerar(
    body: GerarIn,
    request: Request,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> DocumentoOut:
    pac = await _get_paciente(session, user, body.paciente_id)
    await _valida_consentimento(session, user.tenant_id, pac.id)

    # 1) contexto anonimizado (Sprint 5)
    ctx = await montar_contexto_anonimo(session, pac)

    # 2) LLM produz rascunho com placeholders
    rasc = await gerar_documento(
        tipo=body.tipo, finalidade=body.finalidade,
        destinatario=body.destinatario, ctx=ctx, abordagem_prof=user.abordagem,
    )

    # 3) server substitui placeholders localmente
    valores = montar_valores(pac, user, body.finalidade, body.destinatario)
    conteudo_resolvido = substituir_conteudo(rasc.conteudo, valores)

    d = DocumentoCFP(
        tenant_id=user.tenant_id, paciente_id=pac.id, autor_id=user.id,
        tipo=body.tipo, finalidade=body.finalidade, destinatario=body.destinatario,
        conteudo=conteudo_resolvido, status="rascunho",
        provider=rasc.provider_id, prompt_versao=rasc.prompt_versao,
    )
    session.add(d)
    await session.flush()

    ip = request.client.host if request.client else None
    _log(session, tenant_id=user.tenant_id, user_id=user.id, ip=ip,
         acao="DOCUMENTO_GERADO", entidade="DocumentoCFP", entidade_id=str(d.id),
         meta={
             "tipo": body.tipo, "provider": rasc.provider_id,
             "n_evolucoes": ctx.n_evolucoes_assinadas,
             "n_instrumentos": ctx.n_instrumentos_finalizados,
         })
    await session.commit()
    await session.refresh(d)
    return _to_out(d)


# --------------------------------------------------------------------------
# Leitura / edição
# --------------------------------------------------------------------------

@router.get("/documentos/{doc_id}", response_model=DocumentoOut)
async def obter(
    doc_id: str,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> DocumentoOut:
    d = await _get_doc(session, user, doc_id)
    return _to_out(d)


@router.get("/pacientes/{paciente_id}/documentos", response_model=list[DocumentoOut])
async def listar_por_paciente(
    paciente_id: str,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> list[DocumentoOut]:
    pac = await _get_paciente(session, user, paciente_id)
    rows = list((await session.scalars(
        select(DocumentoCFP).where(
            DocumentoCFP.tenant_id == user.tenant_id,
            DocumentoCFP.paciente_id == pac.id,
        ).order_by(desc(DocumentoCFP.criado_em))
    )).all())
    return [_to_out(r) for r in rows]


@router.patch("/documentos/{doc_id}", response_model=DocumentoOut)
async def editar(
    doc_id: str,
    body: DocumentoSalvarIn,
    request: Request,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> DocumentoOut:
    d = await _get_doc(session, user, doc_id)
    if d.status == "assinado":
        raise HTTPException(status.HTTP_409_CONFLICT, "Documento assinado é imutável")
    if body.finalidade is not None:
        d.finalidade = body.finalidade
    if body.destinatario is not None:
        d.destinatario = body.destinatario or None
    if body.conteudo is not None:
        # merge shallow: permite salvar bloco a bloco
        merged = dict(d.conteudo or {})
        for k, v in body.conteudo.items():
            merged[k] = v
        d.conteudo = merged
    ip = request.client.host if request.client else None
    _log(session, tenant_id=user.tenant_id, user_id=user.id, ip=ip,
         acao="DOCUMENTO_EDITADO", entidade="DocumentoCFP", entidade_id=str(d.id),
         meta={"tipo": d.tipo})
    await session.commit()
    await session.refresh(d)
    return _to_out(d)


# --------------------------------------------------------------------------
# Assinar → PDF → Anexo
# --------------------------------------------------------------------------

@router.post("/documentos/{doc_id}/assinar", response_model=DocumentoOut)
async def assinar(
    doc_id: str,
    request: Request,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> DocumentoOut:
    d = await _get_doc(session, user, doc_id)
    if d.status == "assinado":
        raise HTTPException(status.HTTP_409_CONFLICT, "Já assinado")
    if d.autor_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Só o autor pode assinar")
    if not d.conteudo:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Sem conteúdo para assinar")

    # 1) hash de integridade
    d.assinado_em = datetime.now(tz=timezone.utc)
    d.hash_assinatura = _hash_conteudo(d)
    d.status = "assinado"

    # 2) renderiza PDF
    pac = await session.get(Paciente, d.paciente_id)
    if pac is None:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Paciente ausente")

    pac_nome = decrypt_str(pac.nome_cifrado) or "(sem nome)"
    pac_doc = decrypt_str(pac.documento_cifrado)
    data_str = d.assinado_em.strftime("%d/%m/%Y")

    pdf_bytes, sha_pdf = render_documento_pdf(
        tipo=d.tipo, finalidade=d.finalidade, destinatario=d.destinatario,
        conteudo=d.conteudo or {},
        profissional_nome=user.nome, profissional_crp=user.crp,
        paciente_nome=pac_nome, paciente_doc=pac_doc,
        data_emissao_str=data_str, hash_assinatura=d.hash_assinatura,
        timbre=Timbre.from_user(user),
    )

    # 3) anexa ao prontuário
    tpl_titulo = TEMPLATES[d.tipo]["titulo"]
    anexo = AnexoProntuario(
        tenant_id=user.tenant_id, paciente_id=pac.id,
        origem_tipo="documento_cfp", origem_id=d.id,
        titulo=f"{tpl_titulo} — {pac_nome} — {data_str}",
        mimetype="application/pdf",
        bytes=len(pdf_bytes), sha256=sha_pdf,
        arquivo_cifrado=encrypt_bytes(pdf_bytes),
        criado_por=user.id,
    )
    session.add(anexo)
    await session.flush()
    d.anexo_pdf_id = anexo.id

    ip = request.client.host if request.client else None
    _log(session, tenant_id=user.tenant_id, user_id=user.id, ip=ip,
         acao="DOCUMENTO_ASSINADO", entidade="DocumentoCFP", entidade_id=str(d.id),
         meta={"tipo": d.tipo, "hash": d.hash_assinatura, "anexo_bytes": len(pdf_bytes)})
    _log(session, tenant_id=user.tenant_id, user_id=user.id, ip=ip,
         acao="ANEXO_CRIADO", entidade="AnexoProntuario", entidade_id=str(anexo.id),
         meta={"sha256": sha_pdf, "bytes": len(pdf_bytes), "origem_tipo": "documento_cfp"})
    await session.commit()
    await session.refresh(d)
    return _to_out(d)


@router.post("/documentos/{doc_id}/assinar-icp", response_model=DocumentoOut)
async def assinar_icp(
    doc_id: str,
    body: AssinarICPIn,
    request: Request,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> DocumentoOut:
    """Assinatura qualificada ICP-Brasil (PAdES/A1) sobre o PDF gerado.

    A senha do certificado vem no corpo, é usada só em memória e não é persistida.
    Mantém a assinatura simples (hash) e a imutabilidade do documento assinado.
    """
    d = await _get_doc(session, user, doc_id)
    if d.status == "assinado":
        raise HTTPException(status.HTTP_409_CONFLICT, "Já assinado")
    if d.autor_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Só o autor pode assinar")
    if not d.conteudo:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Sem conteúdo para assinar")

    cert = await session.scalar(
        select(CertificadoAssinatura).where(CertificadoAssinatura.user_id == user.id)
    )
    if cert is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            "Nenhum certificado A1 cadastrado. Envie o .pfx em Conta antes de assinar.")

    pac = await session.get(Paciente, d.paciente_id)
    if pac is None:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Paciente ausente")
    pac_nome = decrypt_str(pac.nome_cifrado) or "(sem nome)"
    pac_doc = decrypt_str(pac.documento_cifrado)
    agora = datetime.now(tz=timezone.utc)
    data_str = agora.strftime("%d/%m/%Y")
    hash_conteudo = _hash_conteudo(d)

    # Renderiza o PDF e aplica PAdES ANTES de mutar o documento — se a assinatura
    # falhar (senha errada), nada é persistido e o documento segue rascunho.
    pdf_bytes, _ = render_documento_pdf(
        tipo=d.tipo, finalidade=d.finalidade, destinatario=d.destinatario,
        conteudo=d.conteudo or {}, profissional_nome=user.nome, profissional_crp=user.crp,
        paciente_nome=pac_nome, paciente_doc=pac_doc,
        data_emissao_str=data_str, hash_assinatura=hash_conteudo,
        timbre=Timbre.from_user(user),
    )
    # pyHanko é síncrono e usa o event loop internamente — roda em threadpool
    # (sem loop na thread) para não retornar coroutine nem bloquear o servidor.
    try:
        pfx = decrypt_bytes(cert.arquivo_cifrado) or b""
        signed_pdf = await run_in_threadpool(
            assinar_pades, pdf_bytes, pfx, body.senha,
            reason=f"Assinatura de {TEMPLATES[d.tipo]['titulo']} — {pac_nome}",
        )
    except Exception:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            "Falha ao assinar: verifique a senha do certificado.")

    sha_pdf = hashlib.sha256(signed_pdf).hexdigest()
    d.assinado_em = agora
    d.hash_assinatura = hash_conteudo
    d.status = "assinado"
    d.assinatura_tipo = "icp_brasil"
    d.cert_titular = cert.titular
    d.assinatura_valida = True

    tpl_titulo = TEMPLATES[d.tipo]["titulo"]
    anexo = AnexoProntuario(
        tenant_id=user.tenant_id, paciente_id=pac.id,
        origem_tipo="documento_cfp", origem_id=d.id,
        titulo=f"{tpl_titulo} (ICP-Brasil) — {pac_nome} — {data_str}",
        mimetype="application/pdf", bytes=len(signed_pdf), sha256=sha_pdf,
        arquivo_cifrado=encrypt_bytes(signed_pdf), criado_por=user.id,
    )
    session.add(anexo)
    await session.flush()
    d.anexo_pdf_id = anexo.id

    ip = request.client.host if request.client else None
    _log(session, tenant_id=user.tenant_id, user_id=user.id, ip=ip,
         acao="DOCUMENTO_ASSINADO_ICP", entidade="DocumentoCFP", entidade_id=str(d.id),
         meta={"tipo": d.tipo, "cert_titular": cert.titular, "anexo_bytes": len(signed_pdf)})
    _log(session, tenant_id=user.tenant_id, user_id=user.id, ip=ip,
         acao="ANEXO_CRIADO", entidade="AnexoProntuario", entidade_id=str(anexo.id),
         meta={"sha256": sha_pdf, "bytes": len(signed_pdf), "origem_tipo": "documento_cfp", "assinatura": "icp_brasil"})
    await session.commit()
    await session.refresh(d)
    return _to_out(d)
