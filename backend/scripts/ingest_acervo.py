"""Ingestão do acervo — manifest curado + auto-descoberta recursiva, chunk, embeda, upsert.

Duas fontes de documentos, complementares:
  1. manifest.toml (curado)  — autoritativo p/ os livros com metadados revisados
     (autor, editora, ano) e, crucialmente, o flag is_terceiro=true que aciona o
     guardrail de paráfrase obrigatória. NÃO é sobrescrito pela auto-descoberta.
  2. auto-descoberta         — varre recursivamente acervo/ e ingere cada .pdf que
     NÃO está no manifest, derivando metadados do caminho. Não exige entrada manual.

Idempotente: usa fonte_hash (sha256 do PDF) para pular documentos já ingeridos
e chunk_hash para upsert dos trechos individuais. Commit por documento (resiliente).

Capítulo: PDFs sem outline (TOC) ficariam com capitulo NULL nos chunks; aqui
preenchemos o capitulo com o título do próprio documento quando o outline não o define.

Rodar:
    cd /opt/praxis/backend && uv run python scripts/ingest_acervo.py            # ingere tudo
    cd /opt/praxis/backend && uv run python scripts/ingest_acervo.py --dry-run  # só relatório (sem OpenAI)
    cd /opt/praxis/backend && uv run python scripts/ingest_acervo.py --limit 5  # testa com poucos
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
import tomllib
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

# --- carrega .env do backend ---------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
DOTENV = ROOT / ".env"
if DOTENV.exists():
    for line in DOTENV.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

sys.path.insert(0, str(ROOT))

import psycopg2  # noqa: E402
import psycopg2.extras  # noqa: E402

from app.rag.chunker import chunkify  # noqa: E402
from app.rag.embeddings import embed_batch  # noqa: E402
from app.rag.pdf import PdfDoc, PdfPage, extrair_pdf  # noqa: E402

ACERVO_DIR = ROOT / "acervo"
MANIFEST = ACERVO_DIR / "manifest.toml"

# Extensões de texto que sabemos extrair. Qualquer outra (mp4, png, ...) é pulada+logada.
EXTS_SUPORTADAS = {".pdf", ".docx", ".vtt"}
# PDF escaneado (só imagem) extrai quase nada de texto — abaixo disso, pula e loga.
MIN_TEXT_CHARS = 200
# text-embedding-3-small: US$ 0,02 por 1M de tokens.
EMBED_USD_POR_TOKEN = 0.02 / 1_000_000


# --- extratores de texto (dispatch por extensão) -------------------------------

def _extrair_docx(caminho: Path) -> PdfDoc:
    """Extrai texto de .docx sem dependência externa: é um zip com word/document.xml."""
    import zipfile

    with zipfile.ZipFile(caminho) as z:
        xml = z.read("word/document.xml").decode("utf-8", "ignore")
    # <w:p> = parágrafo (vira quebra de linha); <w:t> = run de texto.
    xml = re.sub(r"</w:p>", "\n", xml)
    xml = re.sub(r"<w:tab\b[^>]*/>", "\t", xml)
    xml = re.sub(r"<[^>]+>", "", xml)  # remove todas as tags restantes
    texto = re.sub(r"[ \t]+", " ", xml)
    texto = re.sub(r"\n{3,}", "\n\n", texto).strip()
    return PdfDoc(caminho=caminho, total_paginas=1, paginas=[PdfPage(numero=1, texto=texto)])


def _extrair_vtt(caminho: Path) -> PdfDoc:
    """Extrai texto de legenda .vtt (WEBVTT): descarta cabeçalho, timestamps e cues."""
    linhas_saida: list[str] = []
    anterior = None
    for raw in caminho.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = raw.strip()
        if not s or s == "WEBVTT" or s.startswith(("NOTE", "STYLE", "REGION")):
            continue
        if "-->" in s:            # linha de timestamp
            continue
        if s.isdigit():           # número sequencial do cue
            continue
        s = re.sub(r"<[^>]+>", "", s)  # tags de estilo inline (<c>, <v>, ...)
        if s and s != anterior:        # colapsa repetições consecutivas (legenda rolante)
            linhas_saida.append(s)
            anterior = s
    texto = "\n".join(linhas_saida).strip()
    return PdfDoc(caminho=caminho, total_paginas=1, paginas=[PdfPage(numero=1, texto=texto)])


def _extrair(caminho: Path) -> PdfDoc:
    ext = caminho.suffix.lower()
    if ext == ".pdf":
        return extrair_pdf(caminho)
    if ext == ".docx":
        return _extrair_docx(caminho)
    if ext == ".vtt":
        return _extrair_vtt(caminho)
    raise ValueError(f"extensão não suportada: {ext}")


@dataclass
class DocSpec:
    """Um PDF a considerar para ingestão, com metadados já resolvidos."""
    slug: str
    titulo: str
    autor: str
    is_terceiro: bool
    pdf_path: Path
    editora: str | None = None
    ano: int | None = None
    origem: str = "auto"  # "manifest" | "auto"


@dataclass
class Report:
    ingeridos: list[tuple[str, int]] = field(default_factory=list)   # (slug, chunks)
    ja_ingeridos: list[str] = field(default_factory=list)            # hash igual, pulados
    duplicados: list[str] = field(default_factory=list)             # mesmo conteúdo já ingerido sob outro slug
    sem_texto: list[str] = field(default_factory=list)               # < MIN_TEXT_CHARS (escaneado)
    erros_extracao: list[str] = field(default_factory=list)          # arquivo corrompido/vazio/ilegível
    ausentes: list[str] = field(default_factory=list)                # manifest aponta p/ arquivo inexistente
    zero_chunks: list[str] = field(default_factory=list)             # extraiu texto mas 0 chunks
    nao_pdf: Counter = field(default_factory=Counter)                # extensão -> contagem
    # dry-run:
    seria_ingerido: list[tuple[str, int, int]] = field(default_factory=list)  # (slug, chunks, tokens)


# ---------------------------------------------------------------------------

def _sync_dsn(url: str) -> str:
    return url.replace("postgresql+asyncpg://", "postgresql://")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for buf in iter(lambda: f.read(1 << 20), b""):
            h.update(buf)
    return h.hexdigest()


def _sha256_chunk(doc_id: str, ordem: int, texto: str) -> str:
    return hashlib.sha256(f"{doc_id}|{ordem}|{texto}".encode("utf-8")).hexdigest()


def _vec_lit(vec: list[float]) -> str:
    """pgvector aceita '[0.1,0.2,...]' como literal."""
    return "[" + ",".join(f"{x:.7f}" for x in vec) + "]"


def _slugify(texto: str) -> str:
    """Slug ascii, estável e legível, derivado de um caminho relativo."""
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    t = t.lower()
    t = re.sub(r"[^a-z0-9/]+", "-", t)   # mantém '/' p/ virar separador de nível
    t = t.replace("/", "--")             # cada nível de pasta vira '--'
    t = re.sub(r"-{3,}", "--", t)        # nunca mais de 2 hifens seguidos
    return t.strip("-") or "doc"


# ---------------------------------------------------------------------------

def _carregar_manifest() -> list[DocSpec]:
    if not MANIFEST.exists():
        return []
    with MANIFEST.open("rb") as f:
        manifest = tomllib.load(f)
    docs: list[DocSpec] = []
    for L in manifest.get("livro", []):
        docs.append(DocSpec(
            slug=L["slug"],
            titulo=L["titulo"],
            autor=L["autor"],
            editora=L.get("editora"),
            ano=L.get("ano"),
            is_terceiro=bool(L.get("is_terceiro", False)),
            pdf_path=ACERVO_DIR / L["arquivo"],
            origem="manifest",
        ))
    return docs


def _descobrir_auto(reservados: set[Path], report: Report, subdir: str | None = None) -> list[DocSpec]:
    """Varre recursivamente acervo/ (ou acervo/<subdir>), ignorando o que o manifest cobre.

    - .pdf/.docx/.vtt -> vira DocSpec (titulo=nome do arquivo; contexto=pasta-pós/subpasta-módulo).
    - outro           -> conta em report.nao_pdf (pula e loga; ex.: .mp4 de aula, imagens).
    """
    base = ACERVO_DIR / subdir if subdir else ACERVO_DIR
    docs: list[DocSpec] = []
    for path in sorted(base.rglob("*")):
        if path.is_dir():
            continue
        if path == MANIFEST or path.name.startswith("."):
            continue
        if path.resolve() in reservados:
            continue  # já tratado pelo manifest (metadados curados)
        if path.suffix.lower() not in EXTS_SUPORTADAS:
            report.nao_pdf[path.suffix.lower() or "(sem-ext)"] += 1
            continue

        rel = path.relative_to(ACERVO_DIR)
        contexto_parts = list(rel.parts[:-1])                 # [pós, módulo, ...]
        editora = " / ".join(contexto_parts) if contexto_parts else "CENAT"
        slug = _slugify(str(rel.with_suffix("")))
        docs.append(DocSpec(
            slug=slug,
            titulo=path.stem,                                  # nome do arquivo sem extensão
            autor="CENAT",                                     # coluna NOT NULL; default do acervo
            editora=editora,                                   # pasta-pós / subpasta-módulo
            ano=None,
            is_terceiro=False,
            pdf_path=path,
            origem="auto",
        ))
    return docs


# ---------------------------------------------------------------------------

def _processar(cur, conn, doc: DocSpec, *, dry_run: bool, report: Report) -> None:
    if not doc.pdf_path.exists():
        report.ausentes.append(doc.slug)
        print(f"[skip] {doc.slug}: arquivo não encontrado ({doc.pdf_path.name})")
        return

    fonte_hash = _sha256_file(doc.pdf_path)
    cur.execute("SELECT id, fonte_hash FROM acervo_documentos WHERE slug = %s", (doc.slug,))
    row = cur.fetchone()
    if row and row[1] == fonte_hash:
        report.ja_ingeridos.append(doc.slug)
        print(f"[ok]   {doc.slug}: já ingerido (hash igual)")
        return

    # Dedup por conteúdo: se este arquivo idêntico já foi ingerido sob QUALQUER slug
    # (mesmo artigo repetido entre pós, ou a pós já ingerida sob outro caminho), pula.
    cur.execute("SELECT slug FROM acervo_documentos WHERE fonte_hash = %s LIMIT 1", (fonte_hash,))
    dup = cur.fetchone()
    if dup:
        report.duplicados.append(doc.slug)
        print(f"[dup]  {doc.slug}: conteúdo idêntico a '{dup[0]}' — pulado.")
        return

    # Extrai ANTES de criar a linha do documento, para poder pular escaneados sem
    # deixar documentos vazios no banco.
    print(f"[run]  {doc.slug}: extraindo...", flush=True)
    try:
        pdf = _extrair(doc.pdf_path)
    except Exception as e:
        report.erros_extracao.append(doc.slug)
        print(f"[erro] {doc.slug}: falha ao extrair ({type(e).__name__}: {e}) — pulado.")
        return
    total_chars = sum(len(p.texto.strip()) for p in pdf.paginas)
    if total_chars < MIN_TEXT_CHARS:
        report.sem_texto.append(doc.slug)
        print(f"[skip] {doc.slug}: sem texto extraível ({total_chars} chars < {MIN_TEXT_CHARS}) — escaneado/sem conteúdo.")
        return

    chunks = chunkify(pdf)
    if not chunks:
        report.zero_chunks.append(doc.slug)
        print(f"[warn] {doc.slug}: 0 chunks extraídos.")
        return

    # Capítulo por documento: sem outline, o chunk herda o título do próprio documento.
    capitulo_default = doc.titulo

    if dry_run:
        tokens = sum(c.tokens for c in chunks)
        report.seria_ingerido.append((doc.slug, len(chunks), tokens))
        print(f"       [dry-run] {pdf.total_paginas} págs → {len(chunks)} chunks (~{tokens} tokens)")
        return

    # --- grava documento (novo ou atualizado) ---
    if row is None:
        cur.execute(
            """
            INSERT INTO acervo_documentos (slug, titulo, autor, editora, ano, is_terceiro, fonte_hash)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
            """,
            (doc.slug, doc.titulo, doc.autor, doc.editora, doc.ano, doc.is_terceiro, fonte_hash),
        )
        doc_id = cur.fetchone()[0]
    else:
        doc_id = row[0]
        cur.execute(
            "UPDATE acervo_documentos SET fonte_hash = %s, atualizado_em = NOW() WHERE id = %s",
            (fonte_hash, doc_id),
        )
        cur.execute("DELETE FROM acervo_chunks WHERE documento_id = %s", (doc_id,))
    conn.commit()

    print(f"       {pdf.total_paginas} páginas → {len(chunks)} chunks")

    # --- embeda em lotes, commit por lote ---
    # 256 por chamada = ~8x menos round-trips à OpenAI que 32; vetores idênticos.
    # Blindado por documento: erro em um doc (ex.: NUL no texto, falha de rede)
    # remove o doc e segue, sem abortar a leva inteira.
    BATCH = 256
    inseridos = 0
    try:
        for start in range(0, len(chunks), BATCH):
            lote = chunks[start:start + BATCH]
            # Postgres não aceita NUL (0x00) em campos text; PDFs às vezes o injetam.
            textos = [c.texto.replace("\x00", "") for c in lote]
            print(f"       embed lote {start // BATCH + 1}/{(len(chunks) + BATCH - 1) // BATCH} ({len(lote)} chunks)...", flush=True)
            vetores = embed_batch(textos)
            rows = []
            for c, texto_limpo, v in zip(lote, textos, vetores):
                chash = _sha256_chunk(str(doc_id), c.ordem, texto_limpo)
                capitulo = (c.capitulo if c.capitulo else capitulo_default).replace("\x00", "")
                rows.append((
                    str(doc_id), c.ordem, capitulo, None,
                    c.pagina_inicio, c.pagina_fim, texto_limpo, c.tokens,
                    chash, _vec_lit(v),
                ))
            psycopg2.extras.execute_batch(
                cur,
                """
                INSERT INTO acervo_chunks
                    (documento_id, ordem, capitulo, secao_titulo, pagina_inicio, pagina_fim,
                     texto, tokens_aprox, chunk_hash, embedding)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s, %s::vector)
                ON CONFLICT (chunk_hash) DO NOTHING
                """,
                rows,
                page_size=50,
            )
            inseridos += len(rows)
            conn.commit()
    except Exception as e:
        conn.rollback()
        # remove o doc (e chunks parciais, via cascade) para reingestão limpa depois
        cur.execute("DELETE FROM acervo_documentos WHERE id = %s", (str(doc_id),))
        conn.commit()
        report.erros_extracao.append(doc.slug)
        print(f"[erro] {doc.slug}: falha na ingestão ({type(e).__name__}: {e}) — doc removido, pulado.")
        return

    report.ingeridos.append((doc.slug, inseridos))
    print(f"[done] {doc.slug}: {inseridos} chunks salvos.")


# ---------------------------------------------------------------------------

def _relatorio(report: Report, *, dry_run: bool) -> None:
    print("\n" + "=" * 70)
    print("RELATÓRIO DE INGESTÃO" + (" (DRY-RUN — nada gravado, sem chamadas à OpenAI)" if dry_run else ""))
    print("=" * 70)

    if dry_run:
        n = len(report.seria_ingerido)
        chunks = sum(c for _, c, _ in report.seria_ingerido)
        tokens = sum(t for _, _, t in report.seria_ingerido)
        custo = tokens * EMBED_USD_POR_TOKEN
        print(f"  Seriam ingeridos      : {n} documentos")
        print(f"  Chunks estimados      : {chunks}")
        print(f"  Tokens estimados      : {tokens:,} (~US$ {custo:.4f} em embeddings)")
    else:
        n = len(report.ingeridos)
        chunks = sum(c for _, c in report.ingeridos)
        print(f"  Ingeridos (novos/atualizados): {n} documentos, {chunks} chunks")

    print(f"  Já ingeridos (idempotente)   : {len(report.ja_ingeridos)}")
    print(f"  Duplicados (mesmo conteúdo)  : {len(report.duplicados)}")
    print(f"  Pulados — sem texto (escaneado, <{MIN_TEXT_CHARS} chars): {len(report.sem_texto)}")
    if report.sem_texto:
        for s in report.sem_texto:
            print(f"        · {s}")
    if report.erros_extracao:
        print(f"  Pulados — erro de extração (corrompido/vazio): {len(report.erros_extracao)}")
        for s in report.erros_extracao:
            print(f"        · {s}")
    if report.zero_chunks:
        print(f"  Pulados — 0 chunks           : {len(report.zero_chunks)}")
        for s in report.zero_chunks:
            print(f"        · {s}")
    total_nao_pdf = sum(report.nao_pdf.values())
    print(f"  Pulados — não-PDF            : {total_nao_pdf}")
    if report.nao_pdf:
        for ext, c in report.nao_pdf.most_common():
            print(f"        · {ext}: {c}")
    if report.ausentes:
        print(f"  Manifest sem arquivo         : {len(report.ausentes)}")
        for s in report.ausentes:
            print(f"        · {s}")
    print("=" * 70)


def main() -> int:
    ap = argparse.ArgumentParser(description="Ingestão do acervo Práxis (manifest + auto-descoberta).")
    ap.add_argument("--dry-run", action="store_true",
                    help="Lista o que seria ingerido (contagem de arquivos, chunks, tokens, custo) sem chamar a OpenAI nem gravar.")
    ap.add_argument("--limit", type=int, default=None,
                    help="Processa no máximo N documentos auto-descobertos (para testar). Não limita o manifest.")
    ap.add_argument("--subdir", default=None,
                    help="Restringe a auto-descoberta a acervo/<SUBDIR> (ex.: uma pós). Ignora o manifest.")
    args = ap.parse_args()

    report = Report()

    if args.subdir:
        manifest_docs = []           # subdir aponta p/ uma pós; manifest é dos livros da raiz
        reservados: set[Path] = set()
    else:
        manifest_docs = _carregar_manifest()
        reservados = {d.pdf_path.resolve() for d in manifest_docs}
    auto_docs = _descobrir_auto(reservados, report, subdir=args.subdir)

    if args.limit is not None:
        auto_docs = auto_docs[:args.limit]

    todos = manifest_docs + auto_docs
    if not todos:
        print("Nada a ingerir: manifest vazio e nenhum PDF em acervo/.", file=sys.stderr)
        return 2

    print(f"Documentos a considerar: {len(manifest_docs)} do manifest + {len(auto_docs)} auto-descobertos"
          + (f" (limitado a {args.limit})" if args.limit is not None else "") + ".")
    if args.dry_run:
        print(">>> DRY-RUN: nenhuma chamada à OpenAI, nenhuma escrita no banco.\n")

    conn = psycopg2.connect(_sync_dsn(os.environ["DATABASE_URL"]))
    conn.autocommit = False
    cur = conn.cursor()
    try:
        for doc in todos:
            _processar(cur, conn, doc, dry_run=args.dry_run, report=report)
    finally:
        cur.close()
        conn.close()

    _relatorio(report, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
