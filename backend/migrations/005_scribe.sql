-- 005: Scribe — evolução gerada por IA (áudio ou resumo).
-- Entrada bruta (transcrição/resumo) cifrada Fernet, apagada ao assinar.

CREATE TABLE IF NOT EXISTS evolucao_geracao (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id         UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
    evolucao_id       UUID NOT NULL UNIQUE REFERENCES evolucoes(id) ON DELETE CASCADE,

    modo              VARCHAR(16) NOT NULL CHECK (modo IN ('audio','resumo')),

    -- Entrada bruta cifrada (mesma chave Fernet dos pacientes)
    entrada_cifrada   BYTEA,
    entrada_tokens    INT,
    entrada_purgada_em TIMESTAMPTZ,          -- setado quando a evolução é assinada

    -- Metadados do áudio (o arquivo em si nunca persiste)
    audio_bytes       INT,
    audio_mimetype    VARCHAR(64),
    audio_hash        VARCHAR(64),
    audio_deletado_em TIMESTAMPTZ,

    -- Metadados da IA
    provider_transc   VARCHAR(80),
    provider_estrut   VARCHAR(80),
    prompt_versao     VARCHAR(16),
    latencia_ms       INT,

    criado_em         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    criado_por        UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS ix_evgeracao_tenant ON evolucao_geracao(tenant_id);
CREATE INDEX IF NOT EXISTS ix_evgeracao_evolucao ON evolucao_geracao(evolucao_id);
