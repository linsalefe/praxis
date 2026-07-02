"""Renderiza o instrumento finalizado como PDF (via PyMuPDF Story).

Layout minimalista: cabeçalho Práxis · nome do instrumento · dados do
paciente/profissional · respostas seção a seção · saída Markdown → HTML ·
atribuição e SHA-256 no rodapé.
"""
from __future__ import annotations

import html
import re
from datetime import datetime, timezone
from typing import Any

from app.pdfutils import render_html_to_pdf
from app.pdftimbre import TIMBRE_CSS, Timbre, timbre_header_html


def _esc(x: str) -> str:
    return html.escape(x or "").replace("\n", "<br/>")


def _md_to_html_simples(md: str) -> str:
    """Cabeçalhos ##/###, **negrito**, listas -/*. Suficiente para os
    rascunhos que os geradores produzem.
    """
    linhas: list[str] = []
    in_list = False
    for raw in md.splitlines():
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
            linhas.append(f"<{tag}>{_esc(m.group(2))}</{tag}>")
            continue

        m = re.match(r"^\s*[-*]\s+(.*)$", l)
        if m:
            if not in_list:
                linhas.append("<ul>")
                in_list = True
            item = _esc(m.group(1))
            item = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", item)
            item = re.sub(r"\*([^*]+)\*", r"<i>\1</i>", item)
            linhas.append(f"<li>{item}</li>")
            continue

        if in_list:
            linhas.append("</ul>")
            in_list = False

        p = _esc(l)
        p = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", p)
        p = re.sub(r"\*([^*]+)\*", r"<i>\1</i>", p)
        linhas.append(f"<p>{p}</p>")
    if in_list:
        linhas.append("</ul>")
    return "\n".join(linhas)


CSS = """
body { font-family: sans-serif; font-size: 10pt; color: #111; }
h1 { font-size: 15pt; margin: 0 0 4pt 0; color: #0b3a80; }
h2 { font-size: 12pt; margin: 12pt 0 4pt 0; color: #0b3a80; border-bottom: 1px solid #ccc; padding-bottom: 2pt; }
h3 { font-size: 11pt; margin: 8pt 0 2pt 0; color: #1a4a99; }
h4 { font-size: 10pt; margin: 6pt 0 2pt 0; color: #1a4a99; }
p, li { margin: 2pt 0; line-height: 1.35; }
.muted { color: #666; font-size: 9pt; }
ul { margin: 2pt 0 2pt 16pt; padding: 0; }
hr { border: 0; border-top: 1px solid #ccc; margin: 8pt 0; }
.field-label { font-weight: bold; color: #333; }
"""


def _likert_html(definicao: dict[str, Any], respostas: dict[str, Any]) -> str:
    """Itens + valores + bloco de escore FACTUAL para instrumentos likert_sum."""
    from app.instrumentos.scoring import pontuar_likert

    opcoes = {o.get("valor"): o.get("rotulo", "") for o in definicao.get("opcoes", [])}
    respmap: dict[str, Any] = (respostas or {}).get("itens", {}) or {}

    partes: list[str] = ["<h2>Respostas coletadas</h2>", "<ul>"]
    for it in definicao.get("itens", []):
        raw = respmap.get(it["id"])
        if raw is None or raw == "":
            v_txt = "<i>(não respondido)</i>"
        else:
            rotulo = opcoes.get(raw, "")
            v_txt = _esc(f"{raw} — {rotulo}" if rotulo else str(raw))
        flag = ' <b>[item de atenção]</b>' if it.get("flag") == "risco" else ""
        partes.append(f'<li><span class="field-label">{_esc(it["texto"])}:</span> {v_txt}{flag}</li>')
    partes.append("</ul>")

    pont = pontuar_likert(definicao, respostas or {})
    partes.append("<h2>Escore (calculado)</h2>")
    if pont["tipo"] == "subescalas":
        partes.append("<ul>")
        for sub in pont["subescores"]:
            faixa = sub.get("faixa_rotulo") or ("incompleta" if not sub["completo"] else "n/d")
            partes.append(
                f'<li><span class="field-label">{_esc(sub["rotulo"])}:</span> '
                f'escore {sub["escore"]} — faixa <b>{_esc(faixa)}</b> '
                f'<span class="muted">({sub["itens_respondidos"]}/{sub["total_itens"]} itens)</span></li>'
            )
        partes.append("</ul>")
    else:
        if pont.get("transformado") is not None:
            escore_txt = f'{pont["transformado"]} (bruto {pont["escore_bruto"]})'
        else:
            escore_txt = str(pont.get("escore"))
        faixa = pont.get("faixa_rotulo") or ("incompleto" if not pont["completo"] else "n/d")
        partes.append(
            f'<p><span class="field-label">Escore:</span> {_esc(escore_txt)} — '
            f'faixa <b>{_esc(faixa)}</b> '
            f'<span class="muted">({pont["itens_respondidos"]}/{pont["total_itens"]} itens)</span></p>'
        )
    partes.append(
        '<p class="muted">Escore e faixa são calculados de forma determinística '
        '(factuais). A interpretação clínica é do profissional.</p>'
    )
    return "\n".join(partes)


def _respostas_html(definicao: dict[str, Any], respostas: dict[str, Any]) -> str:
    if definicao.get("kind") == "likert_sum":
        return _likert_html(definicao, respostas)
    partes: list[str] = ["<h2>Respostas coletadas</h2>"]
    for sec in definicao.get("secoes", []):
        sec_id = sec["id"]
        partes.append(f"<h3>{_esc(sec['titulo'])}</h3>")
        rsec: dict[str, Any] = respostas.get(sec_id) or {}
        if not rsec:
            partes.append('<p class="muted">Sem respostas registradas nesta seção.</p>')
            continue
        partes.append("<ul>")
        for p in sec.get("perguntas", []):
            v = rsec.get(p["id"])
            if v in (None, "", []):
                v_txt = "<i>(não respondido)</i>"
            elif isinstance(v, list):
                v_txt = _esc(", ".join(map(str, v)))
            elif isinstance(v, bool):
                v_txt = "sim" if v else "não"
            else:
                v_txt = _esc(str(v))
            partes.append(
                f'<li><span class="field-label">{_esc(p["label"])}:</span> {v_txt}</li>'
            )
        partes.append("</ul>")
    return "\n".join(partes)


def render_instrumento_pdf(
    *,
    instrumento_titulo: str,
    instrumento_fonte: str | None,
    paciente_nome: str,
    profissional_nome: str,
    profissional_crp: str | None,
    definicao: dict[str, Any],
    respostas: dict[str, Any],
    saida_texto: str,
    timbre: Timbre | None = None,
) -> tuple[bytes, str]:
    """Devolve (pdf_bytes, sha256_hex)."""
    emitido_em = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    respostas_html = _respostas_html(definicao, respostas)
    saida_html = _md_to_html_simples(saida_texto or "_Rascunho da saída não gerado._")
    fonte_txt = _esc(instrumento_fonte or "")
    crp_html = _esc(" · CRP " + profissional_crp) if profissional_crp else ""
    tb = timbre or Timbre.fallback(profissional_nome, profissional_crp)

    html_doc = (
        f"{timbre_header_html(tb)}"
        f"<h1>{_esc(instrumento_titulo)}</h1>"
        f'<p class="muted">Práxis · CENAT · emitido em {_esc(emitido_em)}</p>'
        f"<p><span class=\"field-label\">Paciente:</span> {_esc(paciente_nome)}<br/>"
        f"<span class=\"field-label\">Profissional:</span> {_esc(profissional_nome)}{crp_html}</p>"
        f"<hr/>{respostas_html}"
        f"<h2>Saída revisada</h2>{saida_html}"
        f"<hr/>"
        f'<p class="muted">{fonte_txt}</p>'
    )

    # Renderização consolidada no scaffold compartilhado (pdfutils): mesmo
    # rodapé (paginação + SHA-256 do provisório) e mesma geometria de antes.
    footer = "Práxis · CENAT · pág. {PAGINA}/{TOTAL} · SHA-256: {SHA16}…"
    return render_html_to_pdf(html_doc, CSS + TIMBRE_CSS, footer)
