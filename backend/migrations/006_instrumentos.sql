-- 006: Instrumentos digitais + respostas + anexos ao prontuário.
-- Modelo genérico, extensível para GAM/PTMF/CANMAT futuros.

CREATE TABLE IF NOT EXISTS instrumentos (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tipo       VARCHAR(32) NOT NULL UNIQUE,           -- 'maastricht'|'wrap'|...
    versao     VARCHAR(16) NOT NULL,
    titulo     TEXT NOT NULL,
    descricao  TEXT,
    fonte      TEXT,                                  -- atribuição para o PDF
    definicao  JSONB NOT NULL,                        -- schema declarativo das seções
    criado_em  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS respostas_instrumento (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
    paciente_id     UUID NOT NULL REFERENCES pacientes(id) ON DELETE RESTRICT,
    instrumento_id  UUID NOT NULL REFERENCES instrumentos(id) ON DELETE RESTRICT,
    autor_id        UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,

    status          VARCHAR(16) NOT NULL DEFAULT 'em_andamento'
                    CHECK (status IN ('em_andamento','finalizado')),

    respostas       JSONB NOT NULL DEFAULT '{}'::jsonb,
    saida_texto     TEXT,                             -- markdown editável
    saida_gerada_em TIMESTAMPTZ,
    saida_provider  VARCHAR(80),

    finalizado_em   TIMESTAMPTZ,
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_em   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_resp_tenant   ON respostas_instrumento(tenant_id);
CREATE INDEX IF NOT EXISTS ix_resp_paciente ON respostas_instrumento(paciente_id);
CREATE INDEX IF NOT EXISTS ix_resp_status   ON respostas_instrumento(status);

CREATE TABLE IF NOT EXISTS anexos_prontuario (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
    paciente_id     UUID NOT NULL REFERENCES pacientes(id) ON DELETE RESTRICT,

    origem_tipo     VARCHAR(32) NOT NULL,             -- 'resposta_instrumento'|'upload'
    origem_id       UUID,

    titulo          TEXT NOT NULL,
    mimetype        VARCHAR(64) NOT NULL,
    bytes           INT NOT NULL,
    sha256          CHAR(64) NOT NULL,
    arquivo_cifrado BYTEA NOT NULL,                   -- Fernet AEAD

    criado_em       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    criado_por      UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT
);
CREATE INDEX IF NOT EXISTS ix_anexos_tenant   ON anexos_prontuario(tenant_id);
CREATE INDEX IF NOT EXISTS ix_anexos_paciente ON anexos_prontuario(paciente_id);
CREATE INDEX IF NOT EXISTS ix_anexos_origem   ON anexos_prontuario(origem_tipo, origem_id);
