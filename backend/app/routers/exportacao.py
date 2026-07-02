"""Exportação/portabilidade LGPD (art. 18) — pacote read-only por paciente.

Aditivo e read-only: apenas lê e empacota (ZIP em memória). Não altera nem
apaga nada. Tenant-scoped rígido. A ação é registrada no audit_log (EXPORT).
Exportar ≠ excluir (retenção CFP não faz parte deste sprint).
"""
from __future__ import annotations

import io
import json
import re
import uuid
import zipfile
from datetime import date, datetime, timezone
from typing import Annotated, Any
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select

from app.conformidade.ia_cfp import listar_ia_log
from app.db import current_request_ip
from app.deps import SessionDep, get_current_user
from app.instrumentos.scoring import pontuar_likert
from app.models.audit import AuditLog
from app.models.consentimento import Consentimento
from app.models.documento import DocumentoCFP
from app.models.evolucao import Evolucao
from app.models.instrumentos import AnexoProntuario, Instrumento, RespostaInstrumento
from app.models.paciente import Paciente
from app.models.roteiro import RoteiroSessao
from app.models.sessao import Sessao
from app.models.supervisao import EstudoSupervisao
from app.models.user import User
from app.pdfutils import esc, render_html_to_pdf
from app.security.crypto import decrypt_bytes, decrypt_str

router = APIRouter(tags=["exportacao"])

VERSAO_PACOTE = "1.0"


def _iso(dt: datetime | date | None) -> str | None:
    return dt.isoformat() if dt is not None else None


def _slug(s: str | None, n: int = 48) -> str:
    out = re.sub(r"[^A-Za-z0-9]+", "-", (s or "").strip()).strip("-").lower()
    return out[:n] or "item"


async def _get_paciente(session, user: User, paciente_id: str) -> Paciente:
    try:
        pid = uuid.UUID(paciente_id)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "paciente_id inválido")
    pac = await session.get(Paciente, pid)
    if not pac or pac.tenant_id != user.tenant_id or pac.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Paciente não encontrado")
    return pac


async def _montar_export(session, user: User, pac: Paciente) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Devolve (export_dict, anexos) — anexos = [{nome_arquivo, pdf_bytes, meta}]."""
    tid = user.tenant_id
    pid = pac.id

    # --- Anexos (blobs Fernet) — resolve nomes p/ referência cruzada ---
    anexos_rows = list((await session.scalars(
        select(AnexoProntuario).where(
            AnexoProntuario.tenant_id == tid, AnexoProntuario.paciente_id == pid,
        ).order_by(AnexoProntuario.criado_em)
    )).all())
    anexos_files: list[dict[str, Any]] = []
    anexos_meta: list[dict[str, Any]] = []
    por_origem: dict[str, str] = {}  # origem_id -> caminho no zip
    for a in anexos_rows:
        ext = "pdf" if (a.mimetype or "").endswith("pdf") else "bin"
        nome = f"anexos/{_slug(a.titulo)}_{str(a.id)[:8]}.{ext}"
        anexos_files.append({"nome": nome, "pdf": decrypt_bytes(a.arquivo_cifrado) or b""})
        anexos_meta.append({
            "id": str(a.id), "titulo": a.titulo, "mimetype": a.mimetype,
            "bytes": a.bytes, "sha256": a.sha256, "origem_tipo": a.origem_tipo,
            "origem_id": str(a.origem_id) if a.origem_id else None,
            "criado_em": _iso(a.criado_em), "arquivo": nome,
        })
        if a.origem_id:
            por_origem[str(a.origem_id)] = nome

    # --- Sessões ---
    sessoes = list((await session.scalars(
        select(Sessao).where(Sessao.tenant_id == tid, Sessao.paciente_id == pid).order_by(Sessao.data)
    )).all())
    sessoes_json = [
        {"id": str(s.id), "data": _iso(s.data), "modalidade": s.modalidade,
         "status": s.status, "criado_em": _iso(s.criado_em)}
        for s in sessoes
    ]

    # --- Evoluções (via sessão) ---
    evol_rows = (await session.execute(
        select(Evolucao, Sessao.data)
        .join(Sessao, Sessao.id == Evolucao.sessao_id)
        .where(Evolucao.tenant_id == tid, Sessao.paciente_id == pid)
        .order_by(Evolucao.criado_em)
    )).all()
    evolucoes_json = [
        {"id": str(e.id), "sessao_id": str(e.sessao_id), "sessao_data": _iso(sdata),
         "identificacao": e.identificacao, "demanda_objetivos": e.demanda_objetivos,
         "evolucao": e.evolucao, "encaminhamento": e.encaminhamento,
         "assinado_em": _iso(e.assinado_em), "hash_assinatura": e.hash_assinatura,
         "autor_id": str(e.autor_id), "criado_em": _iso(e.criado_em)}
        for e, sdata in evol_rows
    ]

    # --- Documentos CFP ---
    docs = list((await session.scalars(
        select(DocumentoCFP).where(DocumentoCFP.tenant_id == tid, DocumentoCFP.paciente_id == pid)
        .order_by(DocumentoCFP.criado_em)
    )).all())
    documentos_json = [
        {"id": str(d.id), "tipo": d.tipo, "finalidade": d.finalidade, "destinatario": d.destinatario,
         "conteudo": d.conteudo, "status": d.status, "assinado_em": _iso(d.assinado_em),
         "hash_assinatura": d.hash_assinatura,
         "anexo_ref": por_origem.get(str(d.anexo_pdf_id)) if d.anexo_pdf_id else None,
         "criado_em": _iso(d.criado_em)}
        for d in docs
    ]

    # --- Instrumentos (+ escore factual + ref de anexo) ---
    instr_rows = (await session.execute(
        select(RespostaInstrumento, Instrumento)
        .join(Instrumento, Instrumento.id == RespostaInstrumento.instrumento_id)
        .where(RespostaInstrumento.tenant_id == tid, RespostaInstrumento.paciente_id == pid)
        .order_by(RespostaInstrumento.criado_em)
    )).all()
    instrumentos_json = []
    for r, instr in instr_rows:
        pont = None
        if (instr.definicao or {}).get("kind") == "likert_sum":
            pont = pontuar_likert(instr.definicao, r.respostas or {})
        instrumentos_json.append({
            "id": str(r.id), "instrumento_tipo": instr.tipo, "instrumento_titulo": instr.titulo,
            "instrumento_versao": instr.versao, "respostas": r.respostas, "saida_texto": r.saida_texto,
            "status": r.status, "pontuacao": pont, "anexo_ref": por_origem.get(str(r.id)),
            "criado_em": _iso(r.criado_em), "finalizado_em": _iso(r.finalizado_em),
        })

    # --- Consentimentos ---
    cons = list((await session.scalars(
        select(Consentimento).where(Consentimento.tenant_id == tid, Consentimento.paciente_id == pid)
        .order_by(Consentimento.aceito_em)
    )).all())
    consentimentos_json = [
        {"id": str(c.id), "tipo": c.tipo, "texto_aceito": c.texto_aceito,
         "aceito_por": c.aceito_por, "aceito_em": _iso(c.aceito_em)}
        for c in cons
    ]

    # --- Roteiros de preparação ---
    rots = list((await session.scalars(
        select(RoteiroSessao).where(RoteiroSessao.tenant_id == tid, RoteiroSessao.paciente_id == pid)
        .order_by(RoteiroSessao.criado_em)
    )).all())
    roteiros_json = [
        {"id": str(x.id), "sessao_id": str(x.sessao_id) if x.sessao_id else None,
         "texto": x.texto, "citacoes": x.citacoes, "provider": x.provider, "criado_em": _iso(x.criado_em)}
        for x in rots
    ]

    # --- Supervisão (estudos que referenciam este paciente) ---
    sups = list((await session.scalars(
        select(EstudoSupervisao).where(EstudoSupervisao.tenant_id == tid, EstudoSupervisao.paciente_id == pid)
        .order_by(EstudoSupervisao.criado_em)
    )).all())
    supervisao_json = [
        {"id": str(x.id), "texto_analise": x.texto_analise, "citacoes": x.citacoes,
         "caso_hash": x.caso_hash, "provider": x.provider, "criado_em": _iso(x.criado_em)}
        for x in sups
    ]

    # --- Log de uso de IA (factual, a partir do audit_log) ---
    ia_log_json = await listar_ia_log(session, tid, pid)

    export = {
        "meta": {
            "exportado_em": datetime.now(tz=timezone.utc).isoformat(),
            "por": {"user_id": str(user.id), "nome": user.nome, "crp": user.crp},
            "tenant_id": str(tid),
            "versao_pacote": VERSAO_PACOTE,
            "aviso": ("Pacote LGPD com dados clínicos sensíveis e PII decifrada. "
                      "Proteja o arquivo; a responsabilidade pela guarda é do profissional."),
        },
        "paciente": {
            "id": str(pac.id),
            "nome": decrypt_str(pac.nome_cifrado),
            "contato": decrypt_str(pac.contato_cifrado),
            "nascimento": decrypt_str(pac.nascimento_cifrado),
            "documento": decrypt_str(pac.documento_cifrado),
            "sexo": pac.sexo,
            "reter_ate": _iso(pac.reter_ate),
            "deleted_at": _iso(pac.deleted_at),
            "criado_em": _iso(pac.criado_em),
        },
        "sessoes": sessoes_json,
        "evolucoes": evolucoes_json,
        "documentos": documentos_json,
        "instrumentos": instrumentos_json,
        "anexos": anexos_meta,
        "consentimentos": consentimentos_json,
        "roteiros": roteiros_json,
        "supervisao": supervisao_json,
        "ia_log": ia_log_json,
    }
    export["contagens"] = {
        "sessoes": len(sessoes_json), "evolucoes": len(evolucoes_json),
        "documentos": len(documentos_json), "instrumentos": len(instrumentos_json),
        "anexos": len(anexos_meta), "consentimentos": len(consentimentos_json),
        "roteiros": len(roteiros_json), "supervisao": len(supervisao_json),
        "ia_log": len(ia_log_json),
    }
    return export, anexos_files


def _resumo_pdf(export: dict[str, Any]) -> bytes:
    p = export["paciente"]
    c = export["contagens"]
    ident = " · ".join(x for x in [p.get("nascimento"), p.get("sexo"), p.get("documento")] if x)

    def linha(rot: str, val: str) -> str:
        return f'<p><b>{esc(rot)}:</b> {esc(val)}</p>'

    partes = [
        f"<h1>Resumo de prontuário — {esc(p.get('nome') or '—')}</h1>",
        f'<p class="muted">Práxis · CENAT · exportação LGPD · {esc(export["meta"]["exportado_em"][:19])} UTC</p>',
        linha("Identificação", ident or "—"),
        linha("Contato", p.get("contato") or "—"),
        "<h2>Conteúdo do pacote</h2><ul>",
        f"<li>{c['sessoes']} sessões · {c['evolucoes']} evoluções · {c['documentos']} documentos</li>",
        f"<li>{c['instrumentos']} instrumentos · {c['anexos']} anexos · {c['consentimentos']} consentimentos</li>",
        f"<li>{c['roteiros']} roteiros · {c['supervisao']} estudos de supervisão · {c.get('ia_log', 0)} eventos de IA</li>",
        "</ul>",
    ]

    if export["sessoes"]:
        partes.append("<h2>Sessões</h2><ul>")
        for s in export["sessoes"]:
            partes.append(f"<li>{esc((s['data'] or '')[:16])} · {esc(s['modalidade'])} · <b>{esc(s['status'])}</b></li>")
        partes.append("</ul>")

    if export["evolucoes"]:
        assinadas = sum(1 for e in export["evolucoes"] if e["assinado_em"])
        partes.append(f"<h2>Evoluções</h2><p>{len(export['evolucoes'])} evolução(ões) — {assinadas} assinada(s).</p>")

    if export["instrumentos"]:
        partes.append("<h2>Instrumentos</h2><ul>")
        for i in export["instrumentos"]:
            faixa = ""
            pt = i.get("pontuacao")
            if pt and pt.get("faixa_rotulo"):
                faixa = f" — escore {pt.get('escore')} ({pt['faixa_rotulo']})"
            partes.append(f"<li>{esc(i['instrumento_titulo'])} · {esc(i['status'])}{esc(faixa)}</li>")
        partes.append("</ul>")

    if export["documentos"]:
        partes.append("<h2>Documentos CFP</h2><ul>")
        for d in export["documentos"]:
            partes.append(f"<li>{esc(d['tipo'])} · {esc(d['status'])} · {esc((d['criado_em'] or '')[:10])}</li>")
        partes.append("</ul>")

    if export["consentimentos"]:
        partes.append("<h2>Consentimentos</h2><ul>")
        for c2 in export["consentimentos"]:
            partes.append(f"<li>{esc(c2['tipo'])} — {esc(c2['aceito_por'])} · {esc((c2['aceito_em'] or '')[:10])}</li>")
        partes.append("</ul>")

    if export.get("ia_log"):
        partes.append("<h2>Uso de IA de apoio (Res. CFP 09/2024)</h2>")
        partes.append('<p class="muted">Eventos reais de uso de IA de apoio neste prontuário — todo conteúdo é rascunho revisado e assinado pelo profissional.</p><ul>')
        for ev in export["ia_log"]:
            partes.append(f"<li>{esc((ev['ts'] or '')[:16])} · {esc(ev['recurso'])}</li>")
        partes.append("</ul>")

    partes.append('<hr/><p class="muted">Escores são calculados (factuais). Este resumo acompanha o export.json e os anexos originais no pacote.</p>')

    css = """
    body { font-family: sans-serif; font-size: 10pt; color: #111; }
    h1 { font-size: 15pt; margin: 0 0 4pt 0; color: #0b3a80; }
    h2 { font-size: 12pt; margin: 12pt 0 4pt 0; color: #0b3a80; border-bottom: 1px solid #ccc; }
    p, li { margin: 2pt 0; line-height: 1.35; }
    .muted { color: #666; font-size: 9pt; }
    ul { margin: 2pt 0 2pt 16pt; }
    """
    pdf, _ = render_html_to_pdf("".join(partes), css, "Práxis · CENAT · exportação LGPD · pág. {PAGINA}/{TOTAL}")
    return pdf


@router.get("/pacientes/{paciente_id}/exportar")
async def exportar(
    paciente_id: str,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
    formato: str = "zip",
) -> Response:
    pac = await _get_paciente(session, user, paciente_id)
    export, anexos_files = await _montar_export(session, user, pac)

    # Auditoria da exportação (read-only + trilha LGPD).
    session.add(AuditLog(
        tenant_id=user.tenant_id, user_id=user.id, acao="EXPORT",
        entidade="Paciente", entidade_id=str(pac.id), ip=current_request_ip.get(),
        meta={"formato": formato, **export["contagens"]},
    ))
    await session.commit()

    stamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d")
    base = f"export_{_slug(export['paciente']['nome'])}_{stamp}"
    export_bytes = json.dumps(export, ensure_ascii=False, indent=2).encode("utf-8")

    if formato == "json":
        return Response(
            content=export_bytes, media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={base}.json; filename*=UTF-8''{quote(base)}.json"},
        )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("export.json", export_bytes)
        for a in anexos_files:
            zf.writestr(a["nome"], a["pdf"])
        zf.writestr("resumo.pdf", _resumo_pdf(export))
    data = buf.getvalue()
    return Response(
        content=data, media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={base}.zip; filename*=UTF-8''{quote(base)}.zip"},
    )
