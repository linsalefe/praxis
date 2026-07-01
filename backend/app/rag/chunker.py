"""Chunking do texto por token, com overlap e metadados de página/capítulo."""
from __future__ import annotations

import re
from dataclasses import dataclass

import tiktoken

from app.rag.pdf import PdfDoc

# Encoder padrão da OpenAI para modelos GPT-4/GPT-5 famílias.
_ENC = tiktoken.get_encoding("cl100k_base")

CHUNK_TARGET = 700   # tokens alvo por chunk
CHUNK_OVERLAP = 120  # tokens de overlap entre chunks vizinhos


@dataclass
class Chunk:
    ordem: int
    texto: str
    tokens: int
    capitulo: str | None
    pagina_inicio: int
    pagina_fim: int


def _limpar(texto: str) -> str:
    # remove headers/footers repetidos simples (números soltos e traços)
    linhas = []
    for l in texto.splitlines():
        s = l.strip()
        if re.fullmatch(r"[-–—•·]+", s):
            continue
        if re.fullmatch(r"\d{1,4}", s):  # número de página solto
            continue
        linhas.append(l)
    t = "\n".join(linhas)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def chunkify(pdf: PdfDoc) -> list[Chunk]:
    """Divide o PDF em chunks respeitando ordem de páginas.

    Estratégia: concatena texto por capítulo. Se o texto do capítulo passa
    de CHUNK_TARGET tokens, quebra em sub-chunks com overlap. Para cada
    chunk mantemos pagina_inicio/pagina_fim aproximadas.
    """
    if not pdf.paginas:
        return []

    # agrupa páginas por capítulo (ou por bloco de páginas se sem outline)
    blocos: list[tuple[str | None, list[int], str]] = []
    cur_cap: str | None = object()  # sentinela p/ garantir primeiro flush
    cur_pgs: list[int] = []
    cur_txt: list[str] = []

    def flush():
        if cur_pgs:
            blocos.append((None if cur_cap is object() else cur_cap, list(cur_pgs), "\n\n".join(cur_txt)))

    for p in pdf.paginas:
        cap = p.capitulo
        if cap != cur_cap:
            flush()
            cur_cap = cap
            cur_pgs = []
            cur_txt = []
        cur_pgs.append(p.numero)
        if p.texto.strip():
            cur_txt.append(p.texto)
    flush()

    chunks: list[Chunk] = []
    ordem = 0

    for cap, pgs, texto in blocos:
        texto = _limpar(texto)
        if not texto:
            continue
        ids = _ENC.encode(texto)
        if len(ids) <= CHUNK_TARGET:
            chunks.append(
                Chunk(
                    ordem=ordem,
                    texto=texto,
                    tokens=len(ids),
                    capitulo=cap,
                    pagina_inicio=pgs[0],
                    pagina_fim=pgs[-1],
                )
            )
            ordem += 1
            continue
        # sliding window por tokens, tentando quebrar em fronteira de \n\n
        step = CHUNK_TARGET - CHUNK_OVERLAP
        i = 0
        while i < len(ids):
            j = min(i + CHUNK_TARGET, len(ids))
            sub = _ENC.decode(ids[i:j])
            # ajuste fino: se não é o último e não termina em quebra dupla,
            # tenta cortar no último "\n\n" para manter parágrafo coeso.
            if j < len(ids):
                corte = sub.rfind("\n\n")
                if corte > int(len(sub) * 0.6):
                    sub = sub[:corte]
            sub_tokens = _ENC.encode(sub)
            # Interpolação linear de página baseada na posição no bloco.
            frac_ini = i / max(1, len(ids))
            frac_fim = (i + len(sub_tokens)) / max(1, len(ids))
            pi = pgs[min(int(frac_ini * len(pgs)), len(pgs) - 1)]
            pf = pgs[min(int(frac_fim * len(pgs)), len(pgs) - 1)]
            chunks.append(
                Chunk(
                    ordem=ordem,
                    texto=sub.strip(),
                    tokens=len(sub_tokens),
                    capitulo=cap,
                    pagina_inicio=pi,
                    pagina_fim=pf,
                )
            )
            ordem += 1
            i += max(1, len(sub_tokens) - CHUNK_OVERLAP)
    return chunks
