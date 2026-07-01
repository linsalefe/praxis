"""Gestão do certificado A1 e verificação de assinatura ICP-Brasil.

O `.pfx` é guardado cifrado (Fernet). A senha do PKCS#12 é usada apenas em
memória (upload/assinatura) e NUNCA persistida nem logada.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import delete, select

from app.assinatura.pades import inspecionar, verificar_pades
from app.deps import SessionDep, get_current_user
from app.models.certificado import CertificadoAssinatura
from app.models.documento import DocumentoCFP
from app.models.instrumentos import AnexoProntuario
from app.models.user import User
from app.schemas.assinatura import CertificadoOut, VerificacaoAssinaturaOut
from app.security.crypto import decrypt_bytes, encrypt_bytes

router = APIRouter(tags=["assinatura"])

MAX_PFX = 200 * 1024  # 200 KB — um .pfx A1 é pequeno


def _cert_out(c: CertificadoAssinatura) -> CertificadoOut:
    return CertificadoOut(
        titular=c.titular, emissor=c.emissor, validade_ate=c.validade_ate,
        criado_em=c.criado_em, expirado=c.validade_ate < datetime.now(tz=timezone.utc),
    )


@router.post("/assinatura/certificado", response_model=CertificadoOut, status_code=status.HTTP_201_CREATED)
async def upload_certificado(
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
    arquivo: Annotated[UploadFile, File()],
    senha: Annotated[str, Form()],
) -> CertificadoOut:
    pfx_bytes = await arquivo.read()
    if not pfx_bytes:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Arquivo vazio")
    if len(pfx_bytes) > MAX_PFX:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Arquivo grande demais para um .pfx")

    # Valida senha/formato e extrai metadados (senha só em memória).
    try:
        info = inspecionar(pfx_bytes, senha)
    except Exception:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Certificado ou senha inválidos.")

    # Um certificado ativo por profissional — substitui o anterior.
    await session.execute(delete(CertificadoAssinatura).where(CertificadoAssinatura.user_id == user.id))
    cert = CertificadoAssinatura(
        tenant_id=user.tenant_id, user_id=user.id,
        arquivo_cifrado=encrypt_bytes(pfx_bytes),
        titular=info.titular or "(sem titular)",
        emissor=info.emissor,
        validade_ate=info.validade_ate,
    )
    session.add(cert)
    await session.commit()
    await session.refresh(cert)
    return _cert_out(cert)


@router.get("/assinatura/certificado", response_model=CertificadoOut)
async def obter_certificado(
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> CertificadoOut:
    c = await session.scalar(select(CertificadoAssinatura).where(CertificadoAssinatura.user_id == user.id))
    if c is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Nenhum certificado cadastrado")
    return _cert_out(c)


@router.get("/documentos/{doc_id}/assinatura", response_model=VerificacaoAssinaturaOut)
async def verificar_assinatura(
    doc_id: str,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> VerificacaoAssinaturaOut:
    d = await session.get(DocumentoCFP, uuid.UUID(doc_id))
    if not d or d.tenant_id != user.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Documento não encontrado")

    out = VerificacaoAssinaturaOut(
        assinatura_tipo=d.assinatura_tipo, cert_titular=d.cert_titular, assinado_em=d.assinado_em,
    )
    if d.assinatura_tipo != "icp_brasil" or not d.anexo_pdf_id:
        out.nota = "Assinatura eletrônica simples (hash de integridade)." if d.assinado_em else "Não assinado."
        return out

    anexo = await session.get(AnexoProntuario, d.anexo_pdf_id)
    if anexo is None:
        out.nota = "Anexo assinado não encontrado."
        return out
    v = await run_in_threadpool(verificar_pades, decrypt_bytes(anexo.arquivo_cifrado) or b"")
    out.assinado = v.get("assinado", False)
    out.intacto = v.get("intacto")
    out.valido = v.get("valido")
    out.confiavel = v.get("confiavel")
    out.titular = v.get("titular")
    out.algoritmo = v.get("algoritmo")
    out.nota = ("Assinatura PAdES válida. 'Confiável' exige a AC Raiz ICP-Brasil no validador "
                "(ex.: Adobe/validar.iti.gov.br).") if not v.get("confiavel") else "Assinatura ICP-Brasil confiável."
    return out
