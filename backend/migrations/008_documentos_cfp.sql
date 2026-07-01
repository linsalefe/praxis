-- 008: documentos escritos do psicólogo (Res. CFP 06/2019).
-- Assinatura eletrônica com hash SHA-256; PDF final vai para anexos_prontuario.

CREATE TABLE IF NOT EXISTS documentos_cfp (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
    paciente_id     UUID NOT NULL REFERENCES pacientes(id) ON DELETE RESTRICT,
    autor_id        UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,

    tipo            VARCHAR(24) NOT NULL CHECK (tipo IN
                        ('declaracao','atestado','relatorio','laudo','encaminhamento')),
    finalidade      TEXT NOT NULL,
    destinatario    TEXT,

    conteudo        JSONB NOT NULL DEFAULT '{}'::jsonb,     -- blocos preenchidos
    status          VARCHAR(16) NOT NULL DEFAULT 'rascunho'
                    CHECK (status IN ('rascunho','assinado')),

    provider        VARCHAR(80),                            -- ex.: openai:gpt-5.4-mini
    prompt_versao   VARCHAR(16),

    assinado_em     TIMESTAMPTZ,
    hash_assinatura CHAR(64),
    anexo_pdf_id    UUID REFERENCES anexos_prontuario(id) ON DELETE SET NULL,

    criado_em       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_em   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_docs_tenant   ON documentos_cfp(tenant_id);
CREATE INDEX IF NOT EXISTS ix_docs_paciente ON documentos_cfp(paciente_id, criado_em DESC);
CREATE INDEX IF NOT EXISTS ix_docs_status   ON documentos_cfp(status);
CREATE INDEX IF NOT EXISTS ix_docs_tipo     ON documentos_cfp(tipo);
