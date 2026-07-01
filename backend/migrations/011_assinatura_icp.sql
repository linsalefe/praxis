-- 011: Assinatura digital ICP-Brasil (A1 / PAdES).
-- Aditivo: certificado A1 (.pfx) cifrado por usuário + metadados de assinatura
-- nos documentos CFP. Respeita o salto do 009 (sequência 001–008, 010, 011).

CREATE TABLE IF NOT EXISTS certificados_assinatura (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    arquivo_cifrado BYTEA NOT NULL,          -- .pfx (PKCS#12) cifrado com Fernet
    titular         TEXT NOT NULL,           -- CN/subject do certificado
    emissor         TEXT,                    -- issuer (indica ICP-Brasil)
    validade_ate    TIMESTAMPTZ NOT NULL,    -- notAfter do certificado
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
-- Um certificado ativo por profissional (re-upload substitui).
CREATE UNIQUE INDEX IF NOT EXISTS ux_cert_user ON certificados_assinatura(user_id);

-- Metadados de assinatura nos documentos (a assinatura simples/hash continua).
ALTER TABLE documentos_cfp
    ADD COLUMN IF NOT EXISTS assinatura_tipo   VARCHAR(16) NOT NULL DEFAULT 'simples',  -- simples | icp_brasil
    ADD COLUMN IF NOT EXISTS cert_titular      TEXT,
    ADD COLUMN IF NOT EXISTS assinatura_valida BOOLEAN;
