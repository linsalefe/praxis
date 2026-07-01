-- 003: trilha de auditoria

CREATE TABLE IF NOT EXISTS audit_log (
    id           BIGSERIAL PRIMARY KEY,
    tenant_id    UUID REFERENCES tenants(id) ON DELETE SET NULL,
    user_id      UUID REFERENCES users(id) ON DELETE SET NULL,
    ts           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    acao         VARCHAR(32) NOT NULL,
    entidade     VARCHAR(64) NOT NULL,
    entidade_id  VARCHAR(64),
    ip           INET,
    meta         JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS ix_audit_ts       ON audit_log(ts);
CREATE INDEX IF NOT EXISTS ix_audit_tenant   ON audit_log(tenant_id);
CREATE INDEX IF NOT EXISTS ix_audit_entidade ON audit_log(entidade, entidade_id);
