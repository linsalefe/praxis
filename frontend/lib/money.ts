/** Valores monetários sempre em centavos (inteiro). Nunca float no armazenamento. */

/** Centavos → "R$ 150,00" (pt-BR). */
export function formatCentavos(centavos: number | null | undefined): string {
  if (centavos == null) return "—";
  return (centavos / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

/** Texto do input em reais ("150", "150,50", "1.234,56") → centavos inteiros, ou null. */
export function reaisParaCentavos(texto: string): number | null {
  const limpo = texto.trim().replace(/\./g, "").replace(",", ".");
  if (limpo === "") return null;
  const n = Number(limpo);
  if (!Number.isFinite(n) || n < 0) return null;
  return Math.round(n * 100);
}
