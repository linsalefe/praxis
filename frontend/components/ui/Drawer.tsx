"use client";

/**
 * Drawer — painel lateral (desliza da direita) no estilo Presença.
 * A animação usa a classe .drawer-panel, neutralizada pelo prefers-reduced-motion
 * global. Fecha por Esc, clique no backdrop e botão ×.
 */
import { useEffect } from "react";
import { X } from "lucide-react";
import { useFocusTrap } from "@/lib/useFocusTrap";

export function Drawer({
  open, title, onClose, children,
}: {
  open: boolean;
  title: string;
  onClose: () => void;
  children: React.ReactNode;
}) {
  const trapRef = useFocusTrap<HTMLDivElement>(open);
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={title}
      onClick={onClose}
      style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.4)", display: "flex", justifyContent: "flex-end", zIndex: 60 }}
    >
      <div
        ref={trapRef}
        className="drawer-panel"
        onClick={(e) => e.stopPropagation()}
        style={{
          width: "min(440px, 94%)", height: "100%", background: "var(--surface)",
          borderLeft: "1px solid var(--border)", overflowY: "auto", padding: 20,
          display: "flex", flexDirection: "column", gap: 14,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <h2 style={{ margin: 0, fontSize: 17 }}>{title}</h2>
          <button className="btn" onClick={onClose} aria-label="Fechar"><X size={16} /></button>
        </div>
        {children}
      </div>
    </div>
  );
}
