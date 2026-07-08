-- 021: Módulo de risco (Onda 1.1).
-- Registro de avaliação de risco de suicídio/autolesão (rastreio C-SSRS) + Plano
-- de Segurança (Stanley-Brown). É REGISTRO DE APOIO à decisão clínica, não triagem
-- automática que substitui julgamento profissional — não há alerta/monitoramento
-- automático. Aditivo e idempotente (padrão do projeto, sem Alembic).
--
-- `cssrs` (JSONB) guarda as respostas do rastreio, no mesmo espírito das respostas
-- de instrumento (não cifrado, conteúdo clínico sem identificação de terceiros).
-- `plano_seguranca_cifrado` e `observacoes_cifrado` contêm PII de terceiros
-- (nomes/contatos de rede de apoio) → cifrados em repouso (Fernet), como a PII de
-- paciente. `nivel_risco` é DERIVADO no servidor (fonte única: app/risco/scoring.py)
-- e persistido como um retrato factual do momento da avaliação.

CREATE TABLE IF NOT EXISTS avaliacoes_risco (
    id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
    paciente_id              UUID NOT NULL REFERENCES pacientes(id) ON DELETE RESTRICT,
    criado_por               UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    avaliado_em              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    cssrs                    JSONB NOT NULL DEFAULT '{}'::jsonb,
    nivel_risco              TEXT NOT NULL CHECK (nivel_risco IN ('minimo', 'baixo', 'moderado', 'alto')),
    plano_seguranca_cifrado  BYTEA,
    observacoes_cifrado      BYTEA,
    criado_em                TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_em            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_avaliacoes_risco_paciente ON avaliacoes_risco (paciente_id, avaliado_em DESC);
CREATE INDEX IF NOT EXISTS ix_avaliacoes_risco_tenant ON avaliacoes_risco (tenant_id);
