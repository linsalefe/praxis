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
 * CPF mascarado para exibição por padrão (minimização LGPD): "•••.456.789-••".
 * Se o documento não tiver 11 dígitos (não parece CPF), retorna como está.
 */
export function mascararCpf(doc: string | null | undefined): string {
  if (!doc) return "";
  const d = doc.replace(/\D/g, "");
  if (d.length !== 11) return doc;
  return `•••.${d.slice(3, 6)}.${d.slice(6, 9)}-••`;
}

/** CPF formatado por extenso (usado ao revelar): "123.456.789-00". */
export function formatCpf(doc: string | null | undefined): string {
  if (!doc) return "";
  const d = doc.replace(/\D/g, "");
  if (d.length !== 11) return doc;
  return `${d.slice(0, 3)}.${d.slice(3, 6)}.${d.slice(6, 9)}-${d.slice(9)}`;
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

/**
 * Plural pt-BR: "3 evoluções" / "1 evolução" / "0 evoluções".
 * O sufixo não é flexionável de forma confiável (evolução→evoluções,
 * sessão→sessões), então SEMPRE passe as duas formas por extenso.
 */
export function plural(n: number, singular: string, plural: string): string {
  return `${n} ${n === 1 ? singular : plural}`;
}
