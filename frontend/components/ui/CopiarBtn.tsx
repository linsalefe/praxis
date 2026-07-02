"use client";

import { useState } from "react";
import { Copy, Check } from "lucide-react";
import { toast } from "sonner";

/** Botão de copiar texto para a área de transferência, com feedback breve. */
export function CopiarBtn({
  texto,
  label = "Copiar",
  className = "btn",
  style,
}: {
  texto: string;
  label?: string;
  className?: string;
  style?: React.CSSProperties;
}) {
  const [copiado, setCopiado] = useState(false);

  async function copiar() {
    try {
      await navigator.clipboard.writeText(texto);
      setCopiado(true);
      toast.success("Copiado.");
      setTimeout(() => setCopiado(false), 2000);
    } catch {
      toast.error("Não foi possível copiar.");
    }
  }

  return (
    <button type="button" className={className} onClick={copiar} style={style} aria-label={label}>
      {copiado ? <Check size={14} /> : <Copy size={14} />} {copiado ? "Copiado" : label}
    </button>
  );
}
