"""Substituição de placeholders {{...}} — feita 100% no servidor.

O LLM produz textos com placeholders; aqui trocamos por dados reais
descriptografados localmente. Nada disso vai à OpenAI.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

from app.documentos.templates import PLACEHOLDERS_PERMITIDOS
from app.models.paciente import Paciente
from app.models.user import User
from app.security.crypto import decrypt_str

_PLACEHOLDER_RE = re.compile(r"\{\{\s*([A-Z_]+)\s*\}\}")


def _formatar_data_iso(iso: str | None) -> str:
    if not iso:
        return "(nascimento não informado)"
    try:
        d = datetime.fromisoformat(iso).date()
        return d.strftime("%d/%m/%Y")
    except ValueError:
        return iso


def montar_valores(
    paciente: Paciente,
    profissional: User,
    finalidade: str,
    destinatario: str | None,
    data_emissao: datetime | None = None,
) -> dict[str, str]:
    data_emissao = data_emissao or datetime.now(tz=timezone.utc)
    return {
        "PACIENTE_NOME": decrypt_str(paciente.nome_cifrado) or "(sem nome)",
        "PACIENTE_DOC": decrypt_str(paciente.documento_cifrado) or "(sem documento)",
        "PACIENTE_NASC": _formatar_data_iso(decrypt_str(paciente.nascimento_cifrado)),
        "PROFISSIONAL_NOME": profissional.nome,
        "PROFISSIONAL_CRP": profissional.crp or "(CRP não informado)",
        "DATA_EMISSAO": data_emissao.strftime("%d/%m/%Y"),
        "FINALIDADE": finalidade,
        "DESTINATARIO": destinatario or "(destinatário não informado)",
    }


def substituir(texto: str, valores: dict[str, str]) -> str:
    def repl(m: re.Match[str]) -> str:
        key = m.group(1)
        if key not in PLACEHOLDERS_PERMITIDOS:
            # deixa como está — placeholder desconhecido é sinalizado
            return m.group(0)
        return valores.get(key, m.group(0))
    return _PLACEHOLDER_RE.sub(repl, texto)


def substituir_conteudo(conteudo: dict[str, str], valores: dict[str, str]) -> dict[str, str]:
    return {k: substituir(v or "", valores) for k, v in conteudo.items()}
