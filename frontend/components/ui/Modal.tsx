"use client";

/**
 * Modal — diálogo centralizado no estilo Presença. Consolida as sobreposições
 * hand-rolled (overlay + backdrop + Esc + foco) num único primitivo com focus
 * trap. Espelha o <Drawer>: título opcional (cabeçalho com ×) ou header próprio
 * via children (tabs, PresenceMark). Fecha por Esc, clique no backdrop e ×.
 *
 * `busy`: enquanto true, Esc/backdrop/× não fecham (guarda de request em voo).
 * `elevated`: sobe o zIndex acima de um <Drawer> (ex.: citação sobre o painel).
 */
import { useEffect } from "react";
import { X } from "lucide-react";
import { useFocusTrap } from "@/lib/useFocusTrap";

export function Modal({
  open,
  title,
  onClose,
  children,
  maxWidth = 520,
  busy = false,
  elevated = false,
}: {
  open: boolean;
  title?: string;
  onClose: () => void;
  children: React.ReactNode;
  /** largura máxima do card (default 520). */
  maxWidth?: number | string;
  /** true → Esc/backdrop/× não fecham (request em voo). */
  busy?: boolean;
  /** true → zIndex acima de um Drawer aberto. */
  elevated?: boolean;
}) {
  const trapRef = useFocusTrap<HTMLDivElement>(open);
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape" && !busy) onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, busy, onClose]);

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={title}
      onClick={() => !busy && onClose()}
      style={{
        position: "fixed", inset: 0, background: "var(--scrim)",
        display: "flex", alignItems: "center", justifyContent: "center",
        zIndex: elevated ? "var(--z-overlay-2)" : "var(--z-overlay)", padding: 16,
      }}
    >
      <div
        ref={trapRef}
        className="card"
        onClick={(e) => e.stopPropagation()}
        style={{
          width: "100%", maxWidth, maxHeight: "88vh", overflowY: "auto",
          background: "var(--surface)", boxShadow: "var(--shadow-lg)",
        }}
      >
        {title && (
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
            <h2 style={{ margin: 0, fontSize: 18 }}>{title}</h2>
            <button className="btn btn-icon" onClick={onClose} disabled={busy} aria-label="Fechar"><X size={16} /></button>
          </div>
        )}
        {children}
      </div>
    </div>
  );
}
