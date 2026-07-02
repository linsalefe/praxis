import { statusLabel, statusTom, TOM_CLASSE } from "@/lib/labels";

/**
 * StatusBadge — badge de status com cor semântica.
 * Fonte única de verdade para status na UI: humaniza o enum (statusLabel) e
 * escolhe a cor pelo tom (statusTom → classe badge-* do design system).
 * Nunca renderiza o enum cru. Use em vez de <span className="badge">{status}</span>.
 */
export function StatusBadge({
  status,
  className,
  style,
}: {
  status: string | null | undefined;
  className?: string;
  style?: React.CSSProperties;
}) {
  const cls = TOM_CLASSE[statusTom(status)];
  return (
    <span className={`badge ${cls}${className ? ` ${className}` : ""}`} style={style}>
      {statusLabel(status)}
    </span>
  );
}
