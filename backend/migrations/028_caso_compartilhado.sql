-- 028: PTS colaborativo (Onda 2.1) — compartilhamento de caso com a equipe.
-- Aditivo e idempotente (padrão do projeto, sem Alembic).
--
-- Modelo de compartilhamento: FLAG por caso. Quando `compartilhado = true`, o caso
-- e tudo que pende dele (PTS versionado, matriciamento, rede de apoio) passa a ser
-- visível e editável por TODA a equipe clínica do mesmo tenant (papéis owner e
-- profissional). Quando false, vale o sigilo estrito por profissional (só o dono do
-- paciente e o owner enxergam — comportamento anterior, inalterado).
--
-- O SIGILO CONTINUA SENDO O PADRÃO: casos nascem com compartilhado=false. Ligar o
-- compartilhamento é uma ação deliberada, restrita ao dono do caso ou ao owner, e
-- auditada (AuditLog CASO_COMPARTILHAR). Compartilhar o caso NÃO expõe o restante do
-- prontuário do paciente (sessões, evoluções, avaliações de risco continuam privadas
-- do dono) — só os artefatos colaborativos do próprio caso.

ALTER TABLE casos ADD COLUMN IF NOT EXISTS compartilhado BOOLEAN NOT NULL DEFAULT false;

-- Índice parcial: a listagem "casos compartilhados com a equipe" filtra por isto.
CREATE INDEX IF NOT EXISTS ix_casos_compartilhado ON casos (tenant_id) WHERE compartilhado;
