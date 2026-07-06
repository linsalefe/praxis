-- 020: Revogação de sessão server-side (S3).
-- Blocklist de JWT por jti (logout revoga a sessão atual) + versão de token por
-- usuário para "encerrar todas as sessões" (resposta a comprometimento).
-- Usa versão inteira (não timestamp) para evitar ambiguidade sub-segundo entre
-- revogar e novo login no mesmo instante.

CREATE TABLE IF NOT EXISTS token_revogado (
    jti          TEXT PRIMARY KEY,
    user_id      UUID REFERENCES users(id) ON DELETE CASCADE,
    revogado_em  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    motivo       TEXT
);
CREATE INDEX IF NOT EXISTS ix_token_revogado_revogado_em ON token_revogado (revogado_em);

ALTER TABLE users ADD COLUMN IF NOT EXISTS token_versao INTEGER NOT NULL DEFAULT 0;
