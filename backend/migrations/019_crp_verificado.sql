-- 019: Sinalização de verificação de CRP.
-- O CRP passa a ser validado quanto ao formato no cadastro; a confirmação
-- contra a base do CFP/CRP (quando houver integração) marca crp_verificado.
-- Até lá, contas ficam sinalizadas como "CRP não verificado".

ALTER TABLE users ADD COLUMN IF NOT EXISTS crp_verificado BOOLEAN NOT NULL DEFAULT FALSE;
