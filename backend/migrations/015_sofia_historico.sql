-- 015: histórico de conversas com a Sofia (persistência por usuário/tenant).
-- Uma conversa agrupa turnos (pergunta + resposta + citações). Diferente do
-- audit_log (que guarda só o hash da pergunta), aqui gravamos o texto integral:
-- é o histórico do próprio profissional, escopo tenant/usuário. Não há PII de
-- paciente no conteúdo (a Sofia nunca recebe PII); paciente_id é só a marcação
-- de contexto da consulta. Não altera o guardrail da resposta em si.

CREATE TABLE IF NOT EXISTS sofia_conversas (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
    user_id       UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    paciente_id   UUID REFERENCES pacientes(id) ON DELETE SET NULL,   -- contexto opcional
    titulo        TEXT NOT NULL,                                      -- derivado da 1ª pergunta
    criado_em     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_sofia_conversas_user
    ON sofia_conversas(tenant_id, user_id, atualizado_em DESC);

CREATE TABLE IF NOT EXISTS sofia_turnos (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversa_id   UUID NOT NULL REFERENCES sofia_conversas(id) ON DELETE CASCADE,
    ordem         INT NOT NULL,
    pergunta      TEXT NOT NULL,
    resposta      TEXT NOT NULL,
    citacoes      JSONB NOT NULL DEFAULT '[]'::jsonb,   -- CitacaoOut já serializada
    sem_respaldo  BOOLEAN NOT NULL DEFAULT FALSE,
    usou_paciente BOOLEAN NOT NULL DEFAULT FALSE,
    modelo        TEXT,
    criado_em     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (conversa_id, ordem)
);

CREATE INDEX IF NOT EXISTS ix_sofia_turnos_conversa
    ON sofia_turnos(conversa_id, ordem);
