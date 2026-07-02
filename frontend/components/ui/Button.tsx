"use client";

/**
 * Button (UX-3 U19) — empacota o `.btn` do design system Presença.
 * Variantes mapeiam 1:1 as classes já existentes em globals.css; `loading`
 * desabilita o botão e (opcionalmente) troca o rótulo por `loadingLabel`.
 * Refactor sem mudança visual: o DOM resultante é idêntico ao inline anterior.
 */
import React from "react";

type Variant = "default" | "primary" | "ghost" | "danger";

const VAR_CLASS: Record<Variant, string> = {
  default: "",
  primary: "btn-primary",
  ghost: "btn-ghost",
  danger: "btn-danger",
};

export function Button({
  variant = "default",
  loading = false,
  loadingLabel,
  className,
  disabled,
  children,
  ...rest
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  loading?: boolean;
  loadingLabel?: React.ReactNode;
}) {
  const cls = ["btn", VAR_CLASS[variant], className].filter(Boolean).join(" ");
  return (
    <button className={cls} disabled={disabled || loading} {...rest}>
      {loading && loadingLabel !== undefined ? loadingLabel : children}
    </button>
  );
}
