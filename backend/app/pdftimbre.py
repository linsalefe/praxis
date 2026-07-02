"""Timbre profissional compartilhado dos PDFs (Sprint W1.3).

UM cabeçalho/estilo aplicado a todos os geradores (recibo, documento CFP,
anexo de instrumento, resumo de exportação): nome + registro + contato, com
tipografia e espaçamento consistentes, independente do CSS do corpo de cada
documento. Não altera conteúdo, numeração de recibos nem hash/assinatura —
apenas a apresentação (cabeçalho). Os campos vêm de /conta (users), com
fallback para nome/crp quando vazios.
"""
from __future__ import annotations

import html
from dataclasses import dataclass

# CSS do timbre — visual único em todos os documentos.
TIMBRE_CSS = """
.timbre { border-bottom: 1.5px solid #0b3a80; padding-bottom: 6pt; margin-bottom: 14pt; }
.timbre-nome { font-size: 12pt; font-weight: bold; color: #0b3a80; letter-spacing: -0.2pt; }
.timbre-meta { font-size: 9pt; color: #555; margin-top: 1pt; }
.timbre-sub  { font-size: 8.5pt; color: #777; margin-top: 3pt; }
"""


def _esc(x: str | None) -> str:
    return html.escape(x or "")


@dataclass(frozen=True)
class Timbre:
    nome: str
    registro: str | None
    contato: str | None

    @classmethod
    def from_user(cls, user) -> "Timbre":
        """Constrói o timbre a partir do usuário, com fallback nome/crp."""
        nome = (getattr(user, "nome_exibicao", None) or getattr(user, "nome", "") or "").strip()
        registro = (getattr(user, "registro_profissional", None) or "").strip()
        if not registro and getattr(user, "crp", None):
            registro = f"CRP {user.crp}"
        contato = (getattr(user, "contato_timbre", None) or "").strip()
        return cls(nome=nome, registro=registro or None, contato=contato or None)

    @classmethod
    def fallback(cls, nome: str, crp: str | None) -> "Timbre":
        """Timbre mínimo a partir de nome/crp (compat p/ chamadas sem usuário)."""
        return cls(nome=(nome or "").strip(), registro=(f"CRP {crp}" if crp else None), contato=None)


def timbre_header_html(timbre: Timbre, *, subtitulo: str | None = None) -> str:
    """Banda de cabeçalho: nome em destaque, registro + contato, subtítulo opcional."""
    meta = " · ".join(_esc(p) for p in (timbre.registro, timbre.contato) if p)
    meta_html = f'<div class="timbre-meta">{meta}</div>' if meta else ""
    sub_html = f'<div class="timbre-sub">{_esc(subtitulo)}</div>' if subtitulo else ""
    return (
        '<div class="timbre">'
        f'<div class="timbre-nome">{_esc(timbre.nome)}</div>'
        f"{meta_html}{sub_html}"
        "</div>"
    )
