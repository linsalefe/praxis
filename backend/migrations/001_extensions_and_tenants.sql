-- 001: extensões + tabela de controle de migrações + tenants + users

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS _schema_migrations (
    nome        TEXT PRIMARY KEY,
    aplicado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS tenants (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tipo       VARCHAR(16) NOT NULL CHECK (tipo IN ('solo','clinica')),
    nome       VARCHAR(160) NOT NULL,
    criado_em  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS users (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email               VARCHAR(255) NOT NULL UNIQUE,
    senha_hash          VARCHAR(255) NOT NULL,
    nome                VARCHAR(160) NOT NULL,
    crp                 VARCHAR(32),
    abordagem           VARCHAR(32) CHECK (abordagem IS NULL OR abordagem IN (
                            'dialogo_aberto','ouvir_vozes','gam','ptmf','wrap','reducao_danos','outros'
                        )),
    papel               VARCHAR(16) NOT NULL DEFAULT 'profissional'
                        CHECK (papel IN ('owner','profissional')),
    totp_secret_cifrado BYTEA,
    totp_ativado        BOOLEAN NOT NULL DEFAULT FALSE,
    criado_em           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_em       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_users_tenant ON users(tenant_id);
