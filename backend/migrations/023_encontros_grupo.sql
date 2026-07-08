-- 023: Registro de grupo/oficina/assembleia (Onda 2.2).
-- Sinal de produto mais frequente (35/39 PPCs). Um encontro tem vários
-- participantes: pacientes registrados (paciente_id) e/ou pessoas da comunidade
-- em texto livre (nome cifrado, pois é PII de terceiros).
--
-- Sigilo por profissional: o encontro é do `criado_por` (owner vê todos;
-- profissional vê os seus). Aditivo/idempotente, padrão do projeto.

CREATE TABLE IF NOT EXISTS encontros_grupo (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
    criado_por    UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    tipo          TEXT NOT NULL CHECK (tipo IN ('grupo', 'oficina', 'assembleia')),
    titulo        TEXT NOT NULL,
    data          TIMESTAMPTZ NOT NULL,
    local         TEXT,
    tema          TEXT,
    registro      TEXT,
    criado_em     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_encontros_grupo_tenant ON encontros_grupo (tenant_id, data DESC);
CREATE INDEX IF NOT EXISTS ix_encontros_grupo_criado_por ON encontros_grupo (criado_por);

CREATE TABLE IF NOT EXISTS participantes_encontro (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id          UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
    encontro_id        UUID NOT NULL REFERENCES encontros_grupo(id) ON DELETE CASCADE,
    paciente_id        UUID REFERENCES pacientes(id) ON DELETE SET NULL,
    nome_livre_cifrado BYTEA,  -- PII de participante não-paciente (cifrada)
    presente           BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Ao menos uma identificação: paciente registrado ou nome livre.
    CHECK (paciente_id IS NOT NULL OR nome_livre_cifrado IS NOT NULL)
);
CREATE INDEX IF NOT EXISTS ix_participantes_encontro ON participantes_encontro (encontro_id);
CREATE INDEX IF NOT EXISTS ix_participantes_paciente ON participantes_encontro (paciente_id);
