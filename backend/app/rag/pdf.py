"""Extração de PDF com PyMuPDF, preservando capítulos do outline."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import fitz  # PyMuPDF


@dataclass
class PdfPage:
    numero: int  # 1-based
    texto: str
    capitulo: str | None = None


@dataclass
class PdfDoc:
    caminho: Path
    total_paginas: int
    paginas: list[PdfPage] = field(default_factory=list)


def _outline_por_pagina(doc: "fitz.Document") -> dict[int, str]:
    """Mapa página_1based -> título do último item do outline que a inclui.

    Percorre o outline linear (TOC). Cada item (level, título, página) marca o
    início de um capítulo. Uma página herda o título do último item cuja página
    <= ela. Retorna {} se o PDF não tem outline.
    """
    toc = doc.get_toc(simple=True) or []
    if not toc:
        return {}
    # ordena por página crescente
    items = sorted([(int(pg), (tit or "").strip()) for _lvl, tit, pg in toc if pg and tit], key=lambda x: x[0])
    mapa: dict[int, str] = {}
    if not items:
        return {}
    cursor = 0
    atual = items[0][1]
    for p in range(1, doc.page_count + 1):
        while cursor + 1 < len(items) and items[cursor + 1][0] <= p:
            cursor += 1
            atual = items[cursor][1]
        if p >= items[0][0]:
            mapa[p] = atual
    return mapa


def extrair_pdf(caminho: str | Path) -> PdfDoc:
    caminho = Path(caminho)
    doc = fitz.open(caminho)
    outline = _outline_por_pagina(doc)
    paginas: list[PdfPage] = []
    for i in range(doc.page_count):
        page = doc.load_page(i)
        texto = page.get_text("text") or ""
        # Normaliza whitespace mantendo parágrafos.
        texto = "\n".join(l.rstrip() for l in texto.splitlines())
        paginas.append(
            PdfPage(numero=i + 1, texto=texto, capitulo=outline.get(i + 1))
        )
    total = doc.page_count
    doc.close()
    return PdfDoc(caminho=caminho, total_paginas=total, paginas=paginas)
