"""Ingestão do acervo — lê manifest.toml, extrai PDFs, chunka, embeda, upsert.

Idempotente: usa fonte_hash (sha256 do PDF) para pular documentos já ingeridos
e chunk_hash para upsert dos trechos individuais.

Rodar:
    cd /opt/praxis/backend && uv run python scripts/ingest_acervo.py
"""
from __future__ import annotations

import hashlib
import os
import sys
import tomllib
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
from app.rag.pdf import extrair_pdf  # noqa: E402

ACERVO_DIR = ROOT / "acervo"
MANIFEST = ACERVO_DIR / "manifest.toml"


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


def main() -> int:
    with MANIFEST.open("rb") as f:
        manifest = tomllib.load(f)
    livros = manifest.get("livro", [])
    if not livros:
        print("Manifesto vazio.", file=sys.stderr)
        return 2

    conn = psycopg2.connect(_sync_dsn(os.environ["DATABASE_URL"]))
    conn.autocommit = False
    cur = conn.cursor()

    total_novos_chunks = 0
    for L in livros:
        slug = L["slug"]
        pdf_path = ACERVO_DIR / L["arquivo"]
        if not pdf_path.exists():
            print(f"[skip] {slug}: arquivo não encontrado ({pdf_path.name})")
            continue

        fonte_hash = _sha256_file(pdf_path)
        cur.execute("SELECT id, fonte_hash FROM acervo_documentos WHERE slug = %s", (slug,))
        row = cur.fetchone()

        if row and row[1] == fonte_hash:
            print(f"[ok]   {slug}: já ingerido (hash igual)")
            continue

        if row is None:
            cur.execute(
                """
                INSERT INTO acervo_documentos (slug, titulo, autor, editora, ano, is_terceiro, fonte_hash)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                RETURNING id
                """,
                (slug, L["titulo"], L["autor"], L.get("editora"),
                 L.get("ano"), bool(L.get("is_terceiro", False)), fonte_hash),
            )
            doc_id = cur.fetchone()[0]
        else:
            doc_id = row[0]
            cur.execute(
                "UPDATE acervo_documentos SET fonte_hash = %s, atualizado_em = NOW() WHERE id = %s",
                (fonte_hash, doc_id),
            )
            # PDF mudou — apaga chunks antigos para reingerir
            cur.execute("DELETE FROM acervo_chunks WHERE documento_id = %s", (doc_id,))
        conn.commit()

        # extrai + chunka
        print(f"[run]  {slug}: extraindo...", flush=True)
        pdf = extrair_pdf(pdf_path)
        chunks = chunkify(pdf)
        if not chunks:
            print(f"[warn] {slug}: 0 chunks extraídos.")
            continue
        print(f"       {pdf.total_paginas} páginas → {len(chunks)} chunks")

        # embeda em lotes
        BATCH = 32
        inseridos = 0
        for start in range(0, len(chunks), BATCH):
            lote = chunks[start:start + BATCH]
            textos = [c.texto for c in lote]
            print(f"       embed lote {start // BATCH + 1}/{(len(chunks) + BATCH - 1) // BATCH} ({len(lote)} chunks)...", flush=True)
            vetores = embed_batch(textos)
            rows = []
            for c, v in zip(lote, vetores):
                chash = _sha256_chunk(str(doc_id), c.ordem, c.texto)
                rows.append((
                    str(doc_id), c.ordem, c.capitulo, None,
                    c.pagina_inicio, c.pagina_fim, c.texto, c.tokens,
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

        total_novos_chunks += inseridos
        print(f"[done] {slug}: {inseridos} chunks salvos.")

    cur.close()
    conn.close()
    print(f"\nIngestão concluída. Novos chunks: {total_novos_chunks}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
