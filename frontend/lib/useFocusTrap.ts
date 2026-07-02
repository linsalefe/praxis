"use client";

import { useEffect, useRef } from "react";

const SELETOR_FOCAVEL =
  'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * Focus trap para overlays (Drawer, ConfirmDialog, modais):
 * - foca o 1º elemento focável (ou o container) ao abrir;
 * - mantém Tab/Shift+Tab dentro do container;
 * - devolve o foco ao elemento que estava ativo antes de abrir.
 * Retorna a ref a ligar no container do overlay.
 */
export function useFocusTrap<T extends HTMLElement = HTMLDivElement>(active: boolean) {
  const ref = useRef<T | null>(null);

  useEffect(() => {
    if (!active) return;
    const origem = document.activeElement as HTMLElement | null;
    const container = ref.current;
    if (!container) return;

    const focaveis = () =>
      Array.from(container.querySelectorAll<HTMLElement>(SELETOR_FOCAVEL))
        .filter((el) => el.offsetParent !== null);

    // Foco inicial: 1º campo focável, senão o próprio container.
    const iniciais = focaveis();
    if (iniciais.length) iniciais[0].focus();
    else {
      container.setAttribute("tabindex", "-1");
      container.focus();
    }

    function onKey(e: KeyboardEvent) {
      if (e.key !== "Tab") return;
      const els = focaveis();
      if (!els.length) return;
      const primeiro = els[0];
      const ultimo = els[els.length - 1];
      if (e.shiftKey && document.activeElement === primeiro) {
        e.preventDefault();
        ultimo.focus();
      } else if (!e.shiftKey && document.activeElement === ultimo) {
        e.preventDefault();
        primeiro.focus();
      }
    }

    container.addEventListener("keydown", onKey);
    return () => {
      container.removeEventListener("keydown", onKey);
      // Devolve o foco ao abridor, se ainda existir no DOM.
      if (origem && document.body.contains(origem)) origem.focus();
    };
  }, [active]);

  return ref;
}
