"use client";

import { useEffect } from "react";
import { useFocusTrap } from "@/lib/useFocusTrap";
import { Button } from "@/components/ui/Button";

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
  confirmVariant = "danger",
  busy = false,
  busyLabel,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  description?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  /** Cor do botão de confirmação. "danger" (default) para ações destrutivas;
   *  "primary" para atos não-destrutivos (ex.: assinar). */
  confirmVariant?: "danger" | "primary";
  busy?: boolean;
  /** Rótulo do botão de confirmação enquanto `busy`. Default: "Excluindo…". */
  busyLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const trapRef = useFocusTrap<HTMLDivElement>(open);
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
        background: "var(--scrim)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: "var(--z-overlay)",
        padding: 16,
      }}
    >
      <div
        ref={trapRef}
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
          <Button onClick={onCancel} disabled={busy} type="button">
            {cancelLabel}
          </Button>
          <Button variant={confirmVariant} onClick={onConfirm} disabled={busy} type="button">
            {busy ? (busyLabel ?? "Excluindo…") : confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}
