"use client";

/**
 * SectionTitle (UX-3 U19) — o título de seção padrão do Práxis:
 * `<h2>` muted, 15px, com ícone opcional inline. Refactor sem mudança visual.
 * `margin` é prop porque os sites variam (ex.: "24px 0 8px", "0 0 12px").
 */
import React from "react";

export function SectionTitle({
  icon,
  children,
  margin = "24px 0 8px",
  style,
  ...rest
}: React.HTMLAttributes<HTMLHeadingElement> & {
  icon?: React.ReactNode;
  margin?: string;
}) {
  return (
    <h2 style={{ fontSize: 15, margin, color: "var(--muted)", ...style }} {...rest}>
      {icon ? <>{icon} </> : null}{children}
    </h2>
  );
}
