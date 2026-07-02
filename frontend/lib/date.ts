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
