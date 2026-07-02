-- 014: Conformidade IA-CFP — consentimento de uso de IA.
-- Aditivo: libera 'uso_ia' no CHECK de consentimentos (Res. CFP 09/2024). O log
-- de uso de IA por paciente reusa o audit_log (marcação leve de meta.paciente_id
-- nos pontos de IA) — sem tabela nova.
--
-- Duas travas para o tipo de consentimento (ver telessessão/013): o Literal do
-- Pydantic E este CHECK. Ambos precisam incluir o novo tipo.

ALTER TABLE consentimentos DROP CONSTRAINT IF EXISTS consentimentos_tipo_check;
ALTER TABLE consentimentos ADD CONSTRAINT consentimentos_tipo_check
    CHECK (tipo IN ('tratamento_dados','gravacao','compartilhamento','teleatendimento','uso_ia'));
