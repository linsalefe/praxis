"use client";

/**
 * EmptyState (Y10) — Card centrado com voz factual: ícone opcional, frase e CTA
 * opcional. Substitui os parágrafos muted soltos de "nada aqui ainda".
 */
import { Card } from "@/components/ui/Card";

export function EmptyState({
  icone,
  frase,
  cta,
}: {
  icone?: React.ReactNode;
  frase: string;
  cta?: React.ReactNode;
}) {
  return (
    <Card style={{ textAlign: "center", padding: 28, display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
      {icone && <span aria-hidden style={{ color: "var(--muted)", display: "inline-flex" }}>{icone}</span>}
      <p style={{ margin: 0, color: "var(--muted)", fontSize: 14 }}>{frase}</p>
      {cta}
    </Card>
  );
}
