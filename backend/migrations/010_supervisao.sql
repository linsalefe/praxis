-- 010: Modo Supervisão / Estudo de Caso.
-- (009 fica reservado para a futura integração WhatsApp via Evolution API.)

CREATE TABLE IF NOT EXISTS estudos_supervisao (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
    autor_id      UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,

    origem        VARCHAR(16) NOT NULL CHECK (origem IN ('paciente','avulso')),
    paciente_id   UUID REFERENCES pacientes(id) ON DELETE SET NULL,
    caso_hash     CHAR(64),                 -- sha256 do texto avulso (dedup/audit; sem plaintext)

    texto_analise TEXT NOT NULL,            -- markdown editável
    citacoes      JSONB NOT NULL DEFAULT '[]'::jsonb,
    provider      VARCHAR(80),
    meta          JSONB NOT NULL DEFAULT '{}'::jsonb,

    criado_em     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_supv_tenant   ON estudos_supervisao(tenant_id, criado_em DESC);
CREATE INDEX IF NOT EXISTS ix_supv_paciente ON estudos_supervisao(paciente_id);
CREATE INDEX IF NOT EXISTS ix_supv_autor    ON estudos_supervisao(autor_id);
