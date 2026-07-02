"use client";

/**
 * Field (UX-3 U19) — agrupa label + controle + erro, o padrão de formulário do
 * Práxis. Envolve o controle (children: input/select/textarea) num `<div>`,
 * como já era feito inline. `error` renderiza a mensagem `role="alert"` e marca
 * o controle com `aria-invalid`. Refactor sem mudança visual.
 */
import React from "react";

export function Field({
  label,
  htmlFor,
  error,
  children,
  className,
  style,
}: {
  label: React.ReactNode;
  htmlFor?: string;
  error?: string | null;
  children: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
}) {
  // Propaga aria-invalid ao controle quando há erro, sem alterar o markup.
  const control =
    error && React.isValidElement(children)
      ? React.cloneElement(children as React.ReactElement<{ "aria-invalid"?: boolean }>, { "aria-invalid": true })
      : children;
  return (
    <div className={className} style={style}>
      <label className="label" htmlFor={htmlFor}>{label}</label>
      {control}
      {error && (
        <p role="alert" style={{ color: "var(--danger)", fontSize: 13, margin: "6px 0 0" }}>{error}</p>
      )}
    </div>
  );
}
