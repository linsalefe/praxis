-- 022: Espinha Caso/PTS (Onda 1.2).
-- Introduz `casos` como agregador clínico e `pts_versoes` (Projeto Terapêutico
-- Singular versionado). Aditivo: `sessoes.caso_id` é OPCIONAL — o consultório
-- continua no caminho simples (sessão sem caso); o serviço pendura sessões,
-- risco e (nas próximas ondas) rede/grupos num caso rico.
--
-- Padrão do projeto: tenant-scoped, sigilo por profissional via `criado_por`,
-- migração aditiva e idempotente (sem Alembic). Conteúdo do PTS é narrativa
-- clínica (JSONB em claro, como as evoluções); PII de paciente segue cifrada
-- nas suas tabelas de origem.

CREATE TABLE IF NOT EXISTS casos (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
    paciente_id   UUID NOT NULL REFERENCES pacientes(id) ON DELETE RESTRICT,
    criado_por    UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    titulo        TEXT,
    status        TEXT NOT NULL DEFAULT 'ativo' CHECK (status IN ('ativo', 'encerrado')),
    aberto_em     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    encerrado_em  TIMESTAMPTZ,
    criado_em     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_casos_paciente ON casos (paciente_id);
CREATE INDEX IF NOT EXISTS ix_casos_tenant ON casos (tenant_id);

-- PTS versionado: cada save cria uma nova versão; a "atual" é a de maior número.
CREATE TABLE IF NOT EXISTS pts_versoes (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
    caso_id     UUID NOT NULL REFERENCES casos(id) ON DELETE CASCADE,
    versao      INTEGER NOT NULL,
    conteudo    JSONB NOT NULL DEFAULT '{}'::jsonb,
    criado_por  UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    criado_em   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (caso_id, versao)
);
CREATE INDEX IF NOT EXISTS ix_pts_versoes_caso ON pts_versoes (caso_id, versao DESC);

-- Sessão pode (opcionalmente) pertencer a um caso. SET NULL: apagar o caso não
-- apaga a sessão (histórico clínico preservado).
ALTER TABLE sessoes ADD COLUMN IF NOT EXISTS caso_id UUID REFERENCES casos(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS ix_sessoes_caso ON sessoes (caso_id);
