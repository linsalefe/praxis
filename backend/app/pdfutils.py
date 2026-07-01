"""Utilidades compartilhadas para renderização de PDF via PyMuPDF Story.

Extraído do renderer de instrumentos (Sprint 4) para reuso no Sprint 6
(documentos CFP) e sprints futuras.
"""
from __future__ import annotations

import hashlib
import html
import io
import re

import fitz  # PyMuPDF

MEDIABOX = fitz.paper_rect("a4")
CONTENT_RECT = MEDIABOX + (42, 42, -42, -60)   # deixa faixa inferior p/ rodapé
FOOTER_Y = MEDIABOX.height - 32


def esc(x: str | None) -> str:
    return html.escape(x or "").replace("\n", "<br/>")


def md_to_html(md: str) -> str:
    """Conversor mínimo: cabeçalhos ##/###, **negrito**, *itálico*, listas."""
    linhas: list[str] = []
    in_list = False
    for raw in (md or "").splitlines():
        l = raw.rstrip()
        if not l.strip():
            if in_list:
                linhas.append("</ul>")
                in_list = False
            linhas.append("<br/>")
            continue

        m = re.match(r"^(#{1,4})\s+(.*)$", l)
        if m:
            if in_list:
                linhas.append("</ul>")
                in_list = False
            lvl = len(m.group(1))
            tag = f"h{min(lvl + 1, 5)}"
            linhas.append(f"<{tag}>{esc(m.group(2))}</{tag}>")
            continue

        m = re.match(r"^\s*[-*]\s+(.*)$", l)
        if m:
            if not in_list:
                linhas.append("<ul>")
                in_list = True
            item = esc(m.group(1))
            item = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", item)
            item = re.sub(r"\*([^*]+)\*", r"<i>\1</i>", item)
            linhas.append(f"<li>{item}</li>")
            continue

        if in_list:
            linhas.append("</ul>")
            in_list = False

        p = esc(l)
        p = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", p)
        p = re.sub(r"\*([^*]+)\*", r"<i>\1</i>", p)
        linhas.append(f"<p>{p}</p>")
    if in_list:
        linhas.append("</ul>")
    return "\n".join(linhas)


def render_html_to_pdf(html_doc: str, user_css: str, footer_line: str | None = None) -> tuple[bytes, str]:
    """Renderiza um documento HTML multi-página + adiciona rodapé opcional.

    Devolve (pdf_bytes, sha256_hex).
    """
    buf = io.BytesIO()
    writer = fitz.DocumentWriter(buf)
    story = fitz.Story(html=html_doc, user_css=user_css)

    def rectfn(_i, _f):
        return MEDIABOX, CONTENT_RECT, None

    story.write(writer, rectfn)
    writer.close()
    provisional = buf.getvalue()

    prov_sha = hashlib.sha256(provisional).hexdigest()

    doc = fitz.open(stream=provisional, filetype="pdf")
    total = doc.page_count
    for i, pg in enumerate(doc, start=1):
        line = footer_line or f"Práxis · CENAT · pág. {i}/{total}"
        line = line.replace("{PAGINA}", str(i)).replace("{TOTAL}", str(total)).replace("{SHA16}", prov_sha[:16])
        pg.insert_text(
            (42, FOOTER_Y),
            line,
            fontname="helv", fontsize=7, color=(0.4, 0.4, 0.45),
        )
    out = io.BytesIO()
    doc.save(out)
    doc.close()
    pdf_bytes = out.getvalue()
    return pdf_bytes, hashlib.sha256(pdf_bytes).hexdigest()
