-- 017: Revogação de consentimento (LGPD art. 18 / TCLE-IA).
-- Aditivo: coluna `revogado_em`. Um consentimento com `revogado_em` preenchido
-- deixa de ser "ativo" e passa a bloquear o fluxo correspondente (IA, gravação,
-- teleatendimento). O histórico é preservado (append-only): não apagamos a linha,
-- apenas marcamos a data da revogação — a trilha e o pacote LGPD continuam a
-- mostrar o consentimento e sua revogação.

ALTER TABLE consentimentos ADD COLUMN IF NOT EXISTS revogado_em TIMESTAMPTZ NULL;
