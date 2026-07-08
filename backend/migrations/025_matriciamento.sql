-- 025: Registro de matriciamento / apoio matricial (Onda 2.4).
-- 14/39 PPCs. Registro de um encontro de apoio matricial ligado a um caso: a
-- equipe de referência traz a demanda, há discussão/construção conjunta e
-- combinados. Preserva o sigilo por profissional atual — é um REGISTRO no caso
-- (herda o acesso do caso), não um compartilhamento cross-profissional (esse
-- alarga o sigilo e é decisão de política, deixado para depois).
--
-- Narrativa clínica em claro (como evoluções). Aditivo/idempotente.

CREATE TABLE IF NOT EXISTS matriciamentos (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id          UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
    caso_id            UUID NOT NULL REFERENCES casos(id) ON DELETE CASCADE,
    criado_por         UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    data               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    equipe_referencia  TEXT,
    demanda            TEXT,
    discussao          TEXT,
    combinados         TEXT,
    criado_em          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_em      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_matriciamentos_caso ON matriciamentos (caso_id, data DESC);
