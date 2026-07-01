"""Assinatura digital PAdES (ICP-Brasil, A1/PKCS#12) via pyHanko.

Helpers puros: carregam o `.pfx` **em memória** (a senha nunca é persistida),
assinam os `pdf_bytes` gerados pelo `pdfutils`, e verificam a assinatura.

Segurança: o `.pfx` (identidade legal) é gravado num tempfile 0600 apenas o
tempo necessário para o pyHanko abrir o PKCS#12, e removido em seguida. A senha
vem por parâmetro (do corpo do request) e some ao fim da chamada.
"""
from __future__ import annotations

import io
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime

from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from pyhanko.pdf_utils.reader import PdfFileReader
from pyhanko.sign import PdfSignatureMetadata, signers
from pyhanko.sign.fields import SigSeedSubFilter
from pyhanko.sign.validation import validate_pdf_signature


@dataclass
class CertInfo:
    titular: str | None
    emissor: str | None
    validade_ate: datetime | None


def _carregar_signer(pfx_bytes: bytes, senha: str):
    """Abre o PKCS#12 (A1). `load_pkcs12` exige caminho → tempfile 0600 efêmero."""
    fd, path = tempfile.mkstemp(suffix=".pfx")
    try:
        os.write(fd, pfx_bytes)
        os.close(fd)
        os.chmod(path, 0o600)
        signer = signers.SimpleSigner.load_pkcs12(path, passphrase=senha.encode("utf-8"))
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
    if signer is None:
        raise ValueError("Certificado ou senha inválidos.")
    return signer


def _info(signer) -> CertInfo:
    c = signer.signing_cert  # asn1crypto x509.Certificate
    subj = c.subject.native or {}
    iss = c.issuer.native or {}
    return CertInfo(
        titular=subj.get("common_name") or subj.get("organization_name"),
        emissor=iss.get("common_name") or iss.get("organization_name"),
        validade_ate=c.not_valid_after,
    )


def inspecionar(pfx_bytes: bytes, senha: str) -> CertInfo:
    """Valida senha/formato e extrai titular/emissor/validade — sem persistir nada."""
    return _info(_carregar_signer(pfx_bytes, senha))


def assinar_pades(pdf_bytes: bytes, pfx_bytes: bytes, senha: str, *, reason: str) -> bytes:
    """Aplica assinatura PAdES sobre `pdf_bytes` e devolve o PDF assinado."""
    signer = _carregar_signer(pfx_bytes, senha)
    info = _info(signer)
    writer = IncrementalPdfFileWriter(io.BytesIO(pdf_bytes))
    meta = PdfSignatureMetadata(
        field_name="AssinaturaICP",
        subfilter=SigSeedSubFilter.PADES,
        md_algorithm="sha256",
        reason=reason,
        name=info.titular,
        location="Práxis · CENAT",
    )
    out = signers.sign_pdf(writer, meta, signer)
    return out.getvalue()


def verificar_pades(pdf_bytes: bytes) -> dict:
    """Verifica a assinatura embutida. Sem trust anchor → integridade + validade
    criptográfica + identidade; `confiavel` exige a AC Raiz ICP-Brasil no contexto."""
    reader = PdfFileReader(io.BytesIO(pdf_bytes))
    sigs = list(reader.embedded_signatures)
    if not sigs:
        return {"assinado": False}
    status = validate_pdf_signature(sigs[0])
    cert = getattr(status, "signing_cert", None)
    subj = (cert.subject.native or {}) if cert is not None else {}
    return {
        "assinado": True,
        "intacto": bool(getattr(status, "intact", False)),
        "valido": bool(getattr(status, "valid", False)),
        "confiavel": bool(getattr(status, "trusted", False)),
        "titular": subj.get("common_name"),
        "algoritmo": getattr(status, "md_algorithm", None),
    }
