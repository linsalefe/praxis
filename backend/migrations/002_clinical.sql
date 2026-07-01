-- 002: pacientes (PII cifrada) + sessões + evoluções (estrutura CFP) + consentimentos

CREATE TABLE IF NOT EXISTS pacientes (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
    nome_cifrado        BYTEA NOT NULL,
    contato_cifrado     BYTEA,
    nascimento_cifrado  BYTEA,
    documento_cifrado   BYTEA,
    sexo                VARCHAR(16),
    criado_por          UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    criado_em           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_em       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at          TIMESTAMPTZ,
    reter_ate           DATE
);
CREATE INDEX IF NOT EXISTS ix_pacientes_tenant ON pacientes(tenant_id);
CREATE INDEX IF NOT EXISTS ix_pacientes_ativo  ON pacientes(tenant_id) WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS sessoes (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
    paciente_id   UUID NOT NULL REFERENCES pacientes(id) ON DELETE RESTRICT,
    data          TIMESTAMPTZ NOT NULL,
    modalidade    VARCHAR(16) NOT NULL CHECK (modalidade IN ('presencial','online')),
    status        VARCHAR(16) NOT NULL DEFAULT 'agendada'
                  CHECK (status IN ('agendada','realizada','cancelada','falta')),
    criado_em     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_sessoes_tenant     ON sessoes(tenant_id);
CREATE INDEX IF NOT EXISTS ix_sessoes_paciente   ON sessoes(paciente_id);
CREATE INDEX IF NOT EXISTS ix_sessoes_data       ON sessoes(data);

CREATE TABLE IF NOT EXISTS evolucoes (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id          UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
    sessao_id          UUID NOT NULL REFERENCES sessoes(id) ON DELETE RESTRICT,
    autor_id           UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    identificacao      TEXT,
    demanda_objetivos  TEXT,
    evolucao           TEXT,
    encaminhamento     TEXT,
    assinado_em        TIMESTAMPTZ,
    hash_assinatura    VARCHAR(64),
    criado_em          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_em      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_evolucoes_tenant ON evolucoes(tenant_id);
CREATE INDEX IF NOT EXISTS ix_evolucoes_sessao ON evolucoes(sessao_id);

CREATE TABLE IF NOT EXISTS consentimentos (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
    paciente_id   UUID NOT NULL REFERENCES pacientes(id) ON DELETE RESTRICT,
    tipo          VARCHAR(32) NOT NULL
                  CHECK (tipo IN ('tratamento_dados','gravacao','compartilhamento')),
    texto_aceito  TEXT NOT NULL,
    aceito_por    VARCHAR(160) NOT NULL,
    aceito_em     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_consentimentos_paciente ON consentimentos(paciente_id);
