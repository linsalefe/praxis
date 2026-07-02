-- 016: timbre profissional para os PDFs (Sprint W1.3).
-- Aditivo e opcional: campos editáveis em /conta que compõem o cabeçalho dos
-- documentos gerados (recibo, documento CFP, anexo de instrumento, resumo).
-- Todos NULLable, sem backfill: quando vazios, o timbre cai no fallback já
-- existente (users.nome e users.crp). Não altera conteúdo, numeração de recibos
-- nem hash/assinatura — só a apresentação. `crp` permanece intocado.

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS nome_exibicao         VARCHAR(160),   -- nome no timbre (fallback: nome)
    ADD COLUMN IF NOT EXISTS registro_profissional VARCHAR(64),    -- registro genérico (fallback: crp)
    ADD COLUMN IF NOT EXISTS contato_timbre        VARCHAR(255);   -- contato exibido no cabeçalho
