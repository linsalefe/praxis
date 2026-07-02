/** Formatação de exibição (não altera o dado salvo). */

// Conectores que permanecem minúsculos no meio do nome (pt-BR).
const CONECTORES = new Set(["de", "da", "do", "das", "dos", "e", "di", "du", "del", "la"]);

function capitalizar(palavra: string): string {
  if (!palavra) return palavra;
  // Preserva hifens ("Maria-Clara") capitalizando cada parte.
  return palavra
    .split("-")
    .map((p) => (p ? p.charAt(0).toUpperCase() + p.slice(1) : p))
    .join("-");
}

/**
 * Title case pt-BR para nomes: "JOÃO DA SILVA" → "João da Silva".
 * Conectores (de/da/dos/e…) ficam minúsculos, exceto na primeira posição.
 * Não normaliza o dado — apenas a apresentação.
 */
export function formatNome(nome: string | null | undefined): string {
  if (!nome) return "";
  return nome
    .trim()
    .toLowerCase()
    .split(/\s+/)
    .map((palavra, i) => (i > 0 && CONECTORES.has(palavra) ? palavra : capitalizar(palavra)))
    .join(" ");
}
