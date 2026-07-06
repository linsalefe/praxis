-- 018: Rate-limit / lockout de autenticação (login e 2FA).
-- Contador de tentativas por chave ("acct:<email|user_id>" ou "ip:<ip>"), com
-- bloqueio progressivo. Persistente para sobreviver a restart do worker.

CREATE TABLE IF NOT EXISTS auth_throttle (
    chave           TEXT PRIMARY KEY,
    falhas          INTEGER NOT NULL DEFAULT 0,
    primeira_falha  TIMESTAMPTZ NULL,
    ultima_falha    TIMESTAMPTZ NULL,
    bloqueado_ate   TIMESTAMPTZ NULL
);

-- Purga eventual de chaves antigas pode ser feita por job; índice ajuda.
CREATE INDEX IF NOT EXISTS ix_auth_throttle_ultima_falha ON auth_throttle (ultima_falha);
