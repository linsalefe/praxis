"use client";

/**
 * MenuAcoes (UX-2 U13) — menu "···" para ações secundárias, com uma seção
 * destrutiva separada por divisor (Exportar/Excluir nunca na mesma linha das
 * demais). Acessível: abre por clique/Enter/Espaço, fecha por Esc, clique fora
 * e ao escolher; navegação por ↑/↓; foco volta ao gatilho ao fechar por Esc.
 */
import { useEffect, useRef, useState } from "react";
import { MoreHorizontal } from "lucide-react";

export type AcaoMenu = {
  label: string;
  icon?: React.ReactNode;
  onClick: () => void;
  disabled?: boolean;
};

export function MenuAcoes({
  secundarias,
  destrutivas = [],
  label = "Mais ações",
}: {
  secundarias: AcaoMenu[];
  destrutivas?: AcaoMenu[];
  label?: string;
}) {
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);
  const btnRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") { setOpen(false); btnRef.current?.focus(); }
    };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    // foca o primeiro item ao abrir
    const first = wrapRef.current?.querySelector<HTMLButtonElement>('[role="menuitem"]');
    first?.focus();
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  function onListKey(e: React.KeyboardEvent) {
    if (e.key !== "ArrowDown" && e.key !== "ArrowUp") return;
    e.preventDefault();
    const itens = Array.from(
      wrapRef.current?.querySelectorAll<HTMLButtonElement>('[role="menuitem"]') ?? [],
    );
    const i = itens.indexOf(document.activeElement as HTMLButtonElement);
    const next = e.key === "ArrowDown" ? (i + 1) % itens.length : (i - 1 + itens.length) % itens.length;
    itens[next]?.focus();
  }

  function escolher(acao: AcaoMenu) {
    if (acao.disabled) return;
    setOpen(false);
    acao.onClick();
  }

  const renderItem = (a: AcaoMenu, danger: boolean, key: string) => (
    <button
      key={key}
      role="menuitem"
      className="menu-acoes-item"
      data-danger={danger || undefined}
      disabled={a.disabled}
      onClick={() => escolher(a)}
    >
      {a.icon}
      <span>{a.label}</span>
    </button>
  );

  return (
    <div ref={wrapRef} style={{ position: "relative", display: "inline-block" }}>
      <button
        ref={btnRef}
        className="btn"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={label}
        onClick={() => setOpen((v) => !v)}
      >
        <MoreHorizontal size={16} />
      </button>
      {open && (
        <div role="menu" aria-label={label} className="menu-acoes-panel" onKeyDown={onListKey}>
          {secundarias.map((a, i) => renderItem(a, false, `s${i}`))}
          {destrutivas.length > 0 && (
            <>
              <hr className="divider" style={{ margin: "6px 0" }} />
              {destrutivas.map((a, i) => renderItem(a, true, `d${i}`))}
            </>
          )}
        </div>
      )}
    </div>
  );
}
