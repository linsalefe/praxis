"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { ClipboardList, X } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";

type InstrumentoCatalogo = {
  id: string; tipo: string; versao: string; titulo: string;
  descricao: string | null; fonte: string | null;
};

export function InstrumentoModal({ pacienteId, onClose }: { pacienteId: string; onClose: () => void }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [itens, setItens] = useState<InstrumentoCatalogo[] | null>(null);

  useEffect(() => {
    (async () => {
      try {
        setItens(await api<InstrumentoCatalogo[]>("/instrumentos"));
      } catch (err) {
        toast.error(err instanceof ApiError ? err.message : "Falha ao carregar catálogo");
        setItens([]);
      }
    })();
  }, []);

  async function iniciar(tipo: string) {
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
      <Card style={{ width: "92%", maxWidth: 520, maxHeight: "80vh", overflowY: "auto" }} onClick={(e) => e.stopPropagation()}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <h3 style={{ margin: 0, display: "flex", alignItems: "center", gap: 8 }}>
            <ClipboardList size={18} color="var(--brand-2)" /> Novo instrumento
          </h3>
          <Button onClick={onClose} disabled={busy}><X size={14} /></Button>
        </div>
        <p style={{ color: "var(--muted)", fontSize: 13 }}>
          Escolha o instrumento para esta pessoa. Você pode salvar em rascunho e retomar depois.
        </p>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {itens === null && <p style={{ color: "var(--muted)", fontSize: 13 }}>Carregando catálogo…</p>}
          {itens?.map((i) => (
            <Button
              key={i.tipo}
              disabled={busy}
              onClick={() => iniciar(i.tipo)}
              style={{ justifyContent: "flex-start", padding: "12px 14px" }}
            >
              <div style={{ textAlign: "left" }}>
                <div style={{ fontWeight: 600 }}>
                  {i.titulo}
                  <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--warm-500)" }}> · {i.versao}</span>
                </div>
                {i.descricao && (
                  <div style={{ color: "var(--muted)", fontSize: 12 }}>{i.descricao}</div>
                )}
              </div>
            </Button>
          ))}
        </div>
      </Card>
    </div>
  );
}
