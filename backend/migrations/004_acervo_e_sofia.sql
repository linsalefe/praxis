-- 004: acervo (documentos + chunks com pgvector) para o RAG da Sofia.

CREATE TABLE IF NOT EXISTS acervo_documentos (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug         TEXT UNIQUE NOT NULL,
    titulo       TEXT NOT NULL,
    autor        TEXT NOT NULL,
    editora      TEXT,
    ano          INT,
    is_terceiro  BOOLEAN NOT NULL DEFAULT FALSE,
    fonte_hash   TEXT,                          -- sha256 do PDF de origem
    criado_em    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS acervo_chunks (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    documento_id   UUID NOT NULL REFERENCES acervo_documentos(id) ON DELETE CASCADE,
    ordem          INT NOT NULL,
    capitulo       TEXT,
    secao_titulo   TEXT,
    pagina_inicio  INT,
    pagina_fim     INT,
    texto          TEXT NOT NULL,
    tokens_aprox   INT,
    chunk_hash     TEXT NOT NULL,               -- sha256(documento_id||ordem||texto)
    embedding      VECTOR(1536) NOT NULL,       -- OpenAI text-embedding-3-small
    criado_em      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (documento_id, ordem),
    UNIQUE (chunk_hash)
);

CREATE INDEX IF NOT EXISTS ix_acervo_chunks_doc  ON acervo_chunks(documento_id, ordem);
CREATE INDEX IF NOT EXISTS ix_acervo_chunks_hnsw ON acervo_chunks
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
