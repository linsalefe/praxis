"""Renderização do recibo de atendimento psicológico em PDF.

Reusa `render_html_to_pdf` (pdfutils). Recibo ≠ Nota Fiscal: é o comprovante
que o paciente usa para reembolso de plano; não substitui NF-e/ISS.
"""
from __future__ import annotations

from datetime import datetime

from app.pdfutils import esc, render_html_to_pdf

_CSS = """
* { font-family: sans-serif; color: #1a1a1a; }
h1 { font-size: 18pt; margin: 0 0 2pt; }
.sub { color: #555; font-size: 9pt; margin: 0 0 18pt; }
.valor { font-size: 15pt; font-weight: bold; margin: 14pt 0; }
p { font-size: 10.5pt; line-height: 1.5; margin: 6pt 0; }
.rot { color: #555; font-size: 8.5pt; text-transform: uppercase; letter-spacing: .5pt; margin: 14pt 0 2pt; }
.assinatura { margin-top: 40pt; border-top: 1px solid #999; width: 60%; padding-top: 4pt; font-size: 9.5pt; }
"""


def _reais(centavos: int) -> str:
    s = f"{centavos / 100:,.2f}"
    # pt-BR: milhar com ponto, decimal com vírgula
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


def render_recibo_pdf(
    *,
    numero: int,
    paciente_nome: str,
    paciente_cpf: str | None,
    profissional_nome: str,
    profissional_crp: str | None,
    valor_centavos: int,
    data_sessao: datetime | None,
    emitido_em: datetime,
) -> tuple[bytes, str]:
    cpf = esc(paciente_cpf) if paciente_cpf else "não informado"
    crp = f"CRP {esc(profissional_crp)}" if profissional_crp else "CRP não informado"
    data_str = emitido_em.strftime("%d/%m/%Y")
    ref = (
        f"referente ao atendimento psicológico realizado em {data_sessao.strftime('%d/%m/%Y')}"
        if data_sessao else "referente a atendimento psicológico"
    )

    html_doc = f"""
    <h1>Recibo de Atendimento Psicológico</h1>
    <p class="sub">Recibo nº {numero:04d} · Emitido em {data_str}</p>

    <p class="valor">{_reais(valor_centavos)}</p>

    <p>Recebi de <b>{esc(paciente_nome)}</b> (CPF: {cpf}) a importância de
    <b>{_reais(valor_centavos)}</b>, {ref}.</p>

    <p class="rot">Profissional emissor</p>
    <p>{esc(profissional_nome)} — {crp}</p>

    <p class="rot">Beneficiário</p>
    <p>{esc(paciente_nome)} — CPF: {cpf}</p>

    <p class="assinatura">{esc(profissional_nome)}<br/>{crp}</p>
    """

    footer = f"Práxis · CENAT · Recibo nº {numero:04d} · Documento não fiscal · pág. {{PAGINA}}/{{TOTAL}} · {{SHA16}}"
    return render_html_to_pdf(html_doc, _CSS, footer)
