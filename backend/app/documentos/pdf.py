"""Renderiza documentos CFP como PDF.

Layout formal: papel timbrado Práxis · cabeçalho profissional · corpo por
blocos · área de assinatura eletrônica · rodapé com hash SHA-256.
"""
from __future__ import annotations

from app.documentos.templates import TEMPLATES
from app.pdfutils import esc, render_html_to_pdf
from app.pdftimbre import TIMBRE_CSS, Timbre, timbre_header_html


CSS = """
body { font-family: sans-serif; font-size: 11pt; color: #111; }
h1 { font-size: 17pt; margin: 0 0 4pt 0; color: #0b3a80; letter-spacing: -0.3pt; }
h2 { font-size: 12pt; margin: 14pt 0 4pt 0; color: #0b3a80; border-bottom: 1px solid #ccc; padding-bottom: 2pt; }
p, li { margin: 2pt 0; line-height: 1.4; text-align: justify; }
.muted { color: #666; font-size: 9pt; }
.badge { display: inline-block; padding: 1pt 6pt; border: 1px solid #b3c6e6; border-radius: 4pt; font-size: 8pt; color: #274c8b; }
.header {
  border-bottom: 2px solid #0b3a80; padding-bottom: 8pt; margin-bottom: 14pt;
}
.header .brand { font-weight: bold; font-size: 12pt; color: #0b3a80; }
.header .prof  { font-size: 10pt; color: #333; }
.field-label { font-weight: bold; color: #333; }
.assinatura {
  margin-top: 28pt; padding-top: 12pt; border-top: 1px solid #ccc;
}
.assinatura .linha { border-top: 1px solid #333; margin-top: 40pt; padding-top: 4pt; text-align: center; }
.integridade { color: #666; font-size: 8pt; margin-top: 12pt; }
"""


def _bloco_html(bloco_id: str, texto: str) -> str:
    tpl_bloco = next((b for b in TEMPLATES.values() for x in b["blocos"] if x["id"] == bloco_id), None)  # noqa
    # (não usamos label — construído pelo tipo)
    return f'<p>{esc(texto).replace("<br/>", "<br/>")}</p>'


def render_documento_pdf(
    *,
    tipo: str,
    finalidade: str,
    destinatario: str | None,
    conteudo: dict[str, str],
    profissional_nome: str,
    profissional_crp: str | None,
    paciente_nome: str,
    paciente_doc: str | None,
    data_emissao_str: str,
    hash_assinatura: str,
    timbre: Timbre | None = None,
) -> tuple[bytes, str]:
    template = TEMPLATES[tipo]
    titulo = template["titulo"]
    tb = timbre or Timbre.fallback(profissional_nome, profissional_crp)

    # blocos na ordem do template
    corpo_html_parts: list[str] = []
    for b in template["blocos"]:
        val = conteudo.get(b["id"], "")
        if not val.strip():
            continue
        # Bloco tem título apenas para tipos multi-bloco (relatório/laudo/encaminhamento).
        multi = len(template["blocos"]) > 1
        if multi:
            corpo_html_parts.append(f"<h2>{esc(b['label'])}</h2>")
        corpo_html_parts.append(f"<p>{esc(val)}</p>")

    corpo_html = "\n".join(corpo_html_parts) or "<p><i>Sem conteúdo.</i></p>"

    destinatario_html = (
        f'<p><span class="field-label">Destinatário:</span> {esc(destinatario)}</p>'
        if destinatario else ""
    )

    doc_html = f"""
    {timbre_header_html(tb, subtitulo=f"Documento psicológico · Emitido em {esc(data_emissao_str)}")}

    <h1>{esc(titulo)}</h1>

    <p><span class="field-label">Paciente:</span> {esc(paciente_nome)}
       {(' · Documento: ' + esc(paciente_doc)) if paciente_doc else ''}</p>
    <p><span class="field-label">Finalidade:</span> {esc(finalidade)}</p>
    {destinatario_html}

    {corpo_html}

    <div class="assinatura">
      <div class="linha">
        {esc(profissional_nome)} · CRP {esc(profissional_crp or 'não informado')}
      </div>
      <div class="integridade">
        Assinatura eletrônica registrada · hash de integridade SHA-256:
        <br/><code>{esc(hash_assinatura)}</code>
      </div>
    </div>
    """

    footer = f"Práxis · CENAT · {titulo} · pág. {{PAGINA}}/{{TOTAL}} · SHA-256 {{SHA16}}…"
    return render_html_to_pdf(doc_html, user_css=CSS + TIMBRE_CSS, footer_line=footer)
