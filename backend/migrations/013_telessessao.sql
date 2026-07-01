-- 013: Telessessão (vídeo para atendimento online).
-- Aditivo: URL da sala de vídeo por sessão online. Nome da sala é derivado por
-- HMAC do UUID da sessão (não-adivinhável, sem PII). Provedor default: Jitsi
-- (URL determinística, sem chave). Respeita o salto do 009 e a colisão com o
-- Financeiro (012) — esta é a 013.
--
-- Consentimento de teleatendimento (Res. CFP 11/2018 e atualizações) é exigido
-- antes de liberar a sala; reusa a tabela `consentimentos` com tipo
-- 'teleatendimento' (sem coluna nova).

ALTER TABLE sessoes ADD COLUMN IF NOT EXISTS sala_url TEXT;  -- nullable; só em modalidade=online

-- Libera 'teleatendimento' no CHECK de consentimentos (definido na 002). O
-- schema Pydantic (Literal) e este CHECK são as duas travas — ambas atualizadas.
ALTER TABLE consentimentos DROP CONSTRAINT IF EXISTS consentimentos_tipo_check;
ALTER TABLE consentimentos ADD CONSTRAINT consentimentos_tipo_check
    CHECK (tipo IN ('tratamento_dados','gravacao','compartilhamento','teleatendimento'));
