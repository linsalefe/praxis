-- 012: Financeiro & Recibos.
-- Aditivo: valor por sessão + pagamentos + recibos com numeração sequencial
-- por tenant. Valores sempre em centavos (INTEGER). Respeita o salto do 009
-- (sequência 001–008, 010, 011, 012).
--
-- Recibo ≠ NF-e: este módulo emite recibo (uso do paciente p/ reembolso de
-- plano). NF-e/ISS municipal é integração fiscal separada, fora de escopo.

ALTER TABLE sessoes   ADD COLUMN IF NOT EXISTS valor_centavos        INTEGER;  -- nullable
ALTER TABLE pacientes ADD COLUMN IF NOT EXISTS valor_padrao_centavos INTEGER;  -- nullable; pré-preenche a sessão

CREATE TABLE IF NOT EXISTS pagamentos (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id      UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
    sessao_id      UUID NOT NULL REFERENCES sessoes(id) ON DELETE CASCADE,
    valor_centavos INTEGER NOT NULL,                       -- copiado da sessão no ato (histórico)
    status         VARCHAR(12) NOT NULL DEFAULT 'pago',    -- pendente | pago (só gravamos 'pago')
    forma          VARCHAR(16),                            -- pix|dinheiro|cartao|transferencia
    pago_em        TIMESTAMPTZ,
    recibo_id      UUID,
    criado_por     UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    criado_em      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (sessao_id)                                     -- 1 pagamento por sessão
);
CREATE INDEX IF NOT EXISTS ix_pagamentos_tenant ON pagamentos(tenant_id);

CREATE TABLE IF NOT EXISTS recibos (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id      UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
    numero         INTEGER NOT NULL,                       -- sequencial por tenant
    paciente_id    UUID NOT NULL REFERENCES pacientes(id) ON DELETE RESTRICT,
    sessao_id      UUID REFERENCES sessoes(id) ON DELETE SET NULL,
    valor_centavos INTEGER NOT NULL,
    emitido_por    UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    emitido_em     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    anexo_id       UUID REFERENCES anexos_prontuario(id) ON DELETE SET NULL,
    UNIQUE (tenant_id, numero)
);
CREATE INDEX IF NOT EXISTS ix_recibos_tenant ON recibos(tenant_id);
-- 1 recibo por sessão (reemissão devolve o existente).
CREATE UNIQUE INDEX IF NOT EXISTS ux_recibos_sessao ON recibos(sessao_id) WHERE sessao_id IS NOT NULL;

-- Numeração atômica por tenant (evita a corrida do MAX(numero)+1).
CREATE TABLE IF NOT EXISTS recibo_contadores (
    tenant_id UUID PRIMARY KEY REFERENCES tenants(id) ON DELETE CASCADE,
    proximo   INTEGER NOT NULL
);
