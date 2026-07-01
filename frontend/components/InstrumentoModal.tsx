"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { ClipboardList, X } from "lucide-react";
import { api, ApiError } from "@/lib/api";

const INSTR = [
  { tipo: "maastricht" as const, titulo: "Entrevista de Maastricht", subt: "13 seções · para quem ouve vozes" },
  { tipo: "wrap" as const,       titulo: "WRAP — Plano de bem-estar",     subt: "6 blocos · plano pessoal" },
];

export function InstrumentoModal({ pacienteId, onClose }: { pacienteId: string; onClose: () => void }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);

  async function iniciar(tipo: "maastricht" | "wrap") {
    setBusy(true);
    try {
      const r = await api<{ id: string }>(`/pacientes/${pacienteId}/respostas-instrumento`, {
        method: "POST", body: JSON.stringify({ tipo }),
      });
      router.push(`/instrumentos/${r.id}`);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Falha");
      setBusy(false);
    }
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 50 }}
      onClick={busy ? undefined : onClose}
    >
      <div className="card" style={{ width: "92%", maxWidth: 520 }} onClick={(e) => e.stopPropagation()}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <h3 style={{ margin: 0, display: "flex", alignItems: "center", gap: 8 }}>
            <ClipboardList size={18} color="var(--brand-2)" /> Novo instrumento
          </h3>
          <button className="btn" onClick={onClose} disabled={busy}><X size={14} /></button>
        </div>
        <p style={{ color: "var(--muted)", fontSize: 13 }}>
          Escolha o instrumento para esta pessoa. Você pode salvar em rascunho e retomar depois.
        </p>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {INSTR.map((i) => (
            <button
              key={i.tipo}
              className="btn"
              disabled={busy}
              onClick={() => iniciar(i.tipo)}
              style={{ justifyContent: "flex-start", padding: "12px 14px" }}
            >
              <div style={{ textAlign: "left" }}>
                <div style={{ fontWeight: 600 }}>{i.titulo}</div>
                <div style={{ color: "var(--muted)", fontSize: 12 }}>{i.subt}</div>
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
