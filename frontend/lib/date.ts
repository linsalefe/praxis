/** Datas relativas humanas para a UI — evita ISO cru. Locale pt-BR. */

const DIA_MS = 86_400_000;

function meiaNoite(d: Date): number {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
}

/**
 * "hoje 14:00", "ontem 09:30", "há 3 dias", "em 2 dias", "12/03" ou
 * "12/03/2024" (anos anteriores). Aceita Date | string ISO | null.
 */
export function dataRelativa(input: Date | string | null | undefined): string {
  if (!input) return "—";
  const d = typeof input === "string" ? new Date(input) : input;
  if (isNaN(d.getTime())) return "—";

  const agora = new Date();
  const difDias = Math.round((meiaNoite(d) - meiaNoite(agora)) / DIA_MS);
  const hora = d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });

  if (difDias === 0) return `hoje ${hora}`;
  if (difDias === -1) return `ontem ${hora}`;
  if (difDias === 1) return `amanhã ${hora}`;
  if (difDias < 0 && difDias >= -6) return `há ${-difDias} dias`;
  if (difDias > 0 && difDias <= 6) return `em ${difDias} dias`;

  const mesmoAno = d.getFullYear() === agora.getFullYear();
  return d.toLocaleDateString("pt-BR", mesmoAno
    ? { day: "2-digit", month: "2-digit" }
    : { day: "2-digit", month: "2-digit", year: "numeric" });
}

/**
 * Formato curto absoluto com hora: "qua 08/07 · 14:00" (ou com ano quando não
 * for o corrente). Pensado para a lista de sessões — mono na UI.
 */
export function dataCurtaComHora(input: Date | string | null | undefined): string {
  if (!input) return "—";
  const d = typeof input === "string" ? new Date(input) : input;
  if (isNaN(d.getTime())) return "—";

  const mesmoAno = d.getFullYear() === new Date().getFullYear();
  const dia = d.toLocaleDateString("pt-BR", mesmoAno
    ? { weekday: "short", day: "2-digit", month: "2-digit" }
    : { weekday: "short", day: "2-digit", month: "2-digit", year: "numeric" });
  const hora = d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
  // remove o ponto de abreviações de dia da semana ("qua." → "qua")
  return `${dia.replace(/\./g, "")} · ${hora}`;
}

/**
 * Data-só ("YYYY-MM-DD") formatada como "dd/mm/aaaa", sem escorregar de dia por
 * fuso (a string é lida como data local, não UTC). Aceita também Date/ISO.
 */
export function dataCurta(input: Date | string | null | undefined): string {
  if (!input) return "—";
  if (typeof input === "string") {
    const m = input.match(/^(\d{4})-(\d{2})-(\d{2})/);
    if (m) return `${m[3]}/${m[2]}/${m[1]}`;
  }
  const d = typeof input === "string" ? new Date(input) : input;
  if (isNaN(d.getTime())) return "—";
  return d.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric" });
}

/**
 * Sufixo relativo curto — só quando o evento está a ≤6 dias (passado ou futuro):
 * "hoje", "amanhã", "ontem", "em N dias", "há N dias". Fora dessa janela, "".
 */
export function sufixoRelativoProximo(input: Date | string | null | undefined): string {
  if (!input) return "";
  const d = typeof input === "string" ? new Date(input) : input;
  if (isNaN(d.getTime())) return "";

  const difDias = Math.round((meiaNoite(d) - meiaNoite(new Date())) / DIA_MS);
  if (difDias === 0) return "hoje";
  if (difDias === 1) return "amanhã";
  if (difDias === -1) return "ontem";
  if (difDias > 0 && difDias <= 6) return `em ${difDias} dias`;
  if (difDias < 0 && difDias >= -6) return `há ${-difDias} dias`;
  return "";
}
