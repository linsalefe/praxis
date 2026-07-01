"use client";

import { useEffect } from "react";

/**
 * ConfirmDialog — confirmação para ações irreversíveis (dado clínico não some
 * num clique). Modal Presença com título, descrição e ação destrutiva em
 * .btn-danger. Fecha no Esc / clique fora / Cancelar.
 */
export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel = "Excluir",
  cancelLabel = "Cancelar",
  busy = false,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  description?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !busy) onCancel();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, busy, onCancel]);

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={title}
      onClick={() => !busy && onCancel()}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(42, 38, 32, 0.38)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 60,
        padding: 16,
      }}
    >
      <div
        className="card"
        onClick={(e) => e.stopPropagation()}
        style={{ maxWidth: 440, width: "100%", boxShadow: "var(--shadow-lg)" }}
      >
        <h3 style={{ margin: "0 0 8px", fontSize: 18 }}>{title}</h3>
        {description && (
          <p style={{ margin: "0 0 20px", color: "var(--muted)", fontSize: 14, lineHeight: 1.5 }}>
            {description}
          </p>
        )}
        <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
          <button className="btn" onClick={onCancel} disabled={busy} type="button">
            {cancelLabel}
          </button>
          <button className="btn btn-danger" onClick={onConfirm} disabled={busy} type="button">
            {busy ? "Excluindo…" : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
