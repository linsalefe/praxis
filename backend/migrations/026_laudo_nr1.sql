-- 026: Laudo de risco psicossocial NR-1 (Onda 3.1).
-- Documento ORGANIZACIONAL (sobre uma organização/setor, não um paciente) —
-- avaliação dos fatores de risco psicossocial exigida pela NR-1 (GRO/PGR). Não
-- passa pelo prontuário CFP nem exige consentimento de paciente. Sigilo por
-- profissional pelo criado_por (owner vê todos; profissional vê os seus).
--
-- `fatores` (JSONB): fator_id -> {nivel, observacao}. Nível derivado da avaliação
-- do profissional; narrativa em claro. Aditivo/idempotente.

CREATE TABLE IF NOT EXISTS laudos_nr1 (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
    criado_por    UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    organizacao   TEXT NOT NULL,
    setor         TEXT,
    data          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    fatores       JSONB NOT NULL DEFAULT '{}'::jsonb,
    analise       TEXT,
    recomendacoes TEXT,
    responsavel   TEXT,
    status        TEXT NOT NULL DEFAULT 'rascunho' CHECK (status IN ('rascunho', 'finalizado')),
    finalizado_em TIMESTAMPTZ,
    criado_em     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_laudos_nr1_tenant ON laudos_nr1 (tenant_id, data DESC);
CREATE INDEX IF NOT EXISTS ix_laudos_nr1_criado_por ON laudos_nr1 (criado_por);
