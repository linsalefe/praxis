-- 024: Rede de apoio do caso — genograma/ecomapa (Onda 2.3).
-- 10/39 PPCs pedem explicitamente. Membros pendurados no `caso`: pessoas da
-- família (genograma) e de serviços/comunidade (ecomapa), com tipo de vínculo e
-- força do laço. Topologia estrela (membro ↔ pessoa cuidada) — suficiente para o
-- ecomapa prático; grafo completo entre membros fica para evolução futura.
--
-- `nome_cifrado`: PII de terceiro → cifrada (Fernet), como o nome do paciente.
-- Aditivo/idempotente, padrão do projeto.

CREATE TABLE IF NOT EXISTS membros_rede (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
    caso_id       UUID NOT NULL REFERENCES casos(id) ON DELETE CASCADE,
    criado_por    UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    nome_cifrado  BYTEA NOT NULL,
    papel         TEXT,  -- ex.: mãe, vizinho, ACS, psiquiatra de referência
    tipo_vinculo  TEXT NOT NULL DEFAULT 'outro' CHECK (tipo_vinculo IN ('familiar', 'comunitario', 'servico', 'outro')),
    forca_vinculo TEXT NOT NULL DEFAULT 'forte' CHECK (forca_vinculo IN ('forte', 'fragil', 'conflito')),
    observacoes   TEXT,
    criado_em     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_membros_rede_caso ON membros_rede (caso_id);
