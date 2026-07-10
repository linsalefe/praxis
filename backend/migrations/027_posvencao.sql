-- 027: Posvenção (fecha Onda 1.1 — módulo de risco).
-- Registro do cuidado prestado APÓS uma morte por suicídio: acolhimento dos
-- enlutados (que passam a ter risco aumentado), comunicação segura (prevenção de
-- contágio), articulação da rede, cuidado com a equipe e acompanhamento do luto.
-- É REGISTRO DE APOIO à decisão clínica, como a avaliação de risco (021): não há
-- alerta nem monitoramento automático. Aditivo e idempotente (sem Alembic).
--
-- `paciente_id` é a âncora: pode ser o enlutado em acompanhamento OU o próprio
-- paciente falecido (vinculo_perda = 'proprio_paciente'). `plano_posvencao_cifrado`
-- e `observacoes_cifrado` contêm PII de terceiros (nomes/contatos de enlutados) →
-- cifrados em repouso (Fernet), como no Plano de Segurança da migração 021.
-- `ocorrido_em` é a data do óbito. `status` acompanha o processo (posvenção é
-- contínua, não pontual).

CREATE TABLE IF NOT EXISTS registros_posvencao (
    id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                 UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
    paciente_id               UUID NOT NULL REFERENCES pacientes(id) ON DELETE RESTRICT,
    criado_por                UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    ocorrido_em               DATE NOT NULL,
    vinculo_perda             TEXT NOT NULL CHECK (vinculo_perda IN ('proprio_paciente', 'familiar', 'amigo', 'pessoa_rede', 'outro')),
    status                    TEXT NOT NULL DEFAULT 'aberto' CHECK (status IN ('aberto', 'em_acompanhamento', 'concluido')),
    plano_posvencao_cifrado   BYTEA,
    observacoes_cifrado       BYTEA,
    registrado_em             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    criado_em                 TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_em             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_registros_posvencao_paciente ON registros_posvencao (paciente_id, ocorrido_em DESC);
CREATE INDEX IF NOT EXISTS ix_registros_posvencao_tenant ON registros_posvencao (tenant_id);
