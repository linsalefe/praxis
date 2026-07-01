-- 007: Roteiros pré-sessão gerados por IA a partir do histórico anonimizado.

CREATE TABLE IF NOT EXISTS roteiros_sessao (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
    paciente_id   UUID NOT NULL REFERENCES pacientes(id) ON DELETE RESTRICT,
    sessao_id     UUID REFERENCES sessoes(id) ON DELETE SET NULL,
    autor_id      UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,

    texto         TEXT NOT NULL,               -- Markdown editável
    citacoes      JSONB NOT NULL DEFAULT '[]'::jsonb,
    provider      VARCHAR(80),
    meta          JSONB NOT NULL DEFAULT '{}'::jsonb,  -- n_evolucoes, n_instrumentos usados etc.

    criado_em     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_roteiros_tenant   ON roteiros_sessao(tenant_id);
CREATE INDEX IF NOT EXISTS ix_roteiros_paciente ON roteiros_sessao(paciente_id, criado_em DESC);
CREATE INDEX IF NOT EXISTS ix_roteiros_sessao   ON roteiros_sessao(sessao_id);
