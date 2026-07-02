"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { FileSignature, X } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";

type Tipo = "declaracao" | "atestado" | "relatorio" | "laudo" | "encaminhamento";

type Template = {
  tipo: Tipo;
  titulo: string;
  descricao: string;
  blocos: { id: string; label: string }[];
};

const REQUER_DEST: Set<Tipo> = new Set(["encaminhamento"]);

export function DocumentoModal({
  pacienteId, onClose,
}: {
  pacienteId: string;
  onClose: () => void;
}) {
  const router = useRouter();
  const [templates, setTemplates] = useState<Template[]>([]);
  const [tipo, setTipo] = useState<Tipo>("declaracao");
  const [finalidade, setFinalidade] = useState("");
  const [destinatario, setDestinatario] = useState("");
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try { setTemplates(await api<Template[]>("/documentos/templates")); }
      catch (err) { toast.error(err instanceof ApiError ? err.message : "Falha"); }
    })();
  }, []);

  async function gerar() {
    if (finalidade.trim().length < 3) { toast.error("Preencha a finalidade."); return; }
    setBusy("Gerando…");
    try {
      const body: Record<string, unknown> = {
        paciente_id: pacienteId, tipo, finalidade,
      };
      if (REQUER_DEST.has(tipo) && destinatario.trim()) body.destinatario = destinatario;
      const d = await api<{ id: string }>("/documentos/gerar", {
        method: "POST", body: JSON.stringify(body),
      });
      router.push(`/documentos/${d.id}`);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Falha ao gerar");
      setBusy(null);
    }
  }

  const tplAtual = templates.find((t) => t.tipo === tipo);

  return (
    <div
      role="dialog" aria-modal="true"
      style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.55)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 50 }}
      onClick={busy ? undefined : onClose}
    >
      <Card style={{ width: "92%", maxWidth: 620 }} onClick={(e) => e.stopPropagation()}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <h3 style={{ margin: 0, display: "flex", alignItems: "center", gap: 8 }}>
            <FileSignature size={18} color="var(--brand-2)" /> Gerar documento
          </h3>
          <Button onClick={onClose} disabled={!!busy}><X size={14} /></Button>
        </div>
        <p style={{ color: "var(--muted)", fontSize: 13 }}>
          Escolha o tipo (Res. CFP 06/2019). O rascunho vem editável e a assinatura permanece manual.
        </p>

        <label className="label">Tipo</label>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px,1fr))", gap: 8, marginBottom: 12 }}>
          {templates.map((t) => {
            const selected = t.tipo === tipo;
            return (
              <button
                key={t.tipo} type="button"
                onClick={() => setTipo(t.tipo)}
                disabled={!!busy}
                style={{
                  padding: "10px 12px", textAlign: "left",
                  borderRadius: 8, cursor: "pointer",
                  border: `1px solid ${selected ? "var(--teal-300)" : "var(--border)"}`,
                  background: selected ? "var(--teal-50)" : "var(--surface-2)",
                  color: "var(--text)",
                }}
              >
                <div style={{ fontWeight: 600, marginBottom: 2 }}>{t.titulo}</div>
                <div style={{ color: "var(--muted)", fontSize: 11 }}>{t.blocos.length} bloco(s)</div>
              </button>
            );
          })}
        </div>

        {tplAtual && (
          <p style={{ color: "var(--muted)", fontSize: 12, margin: "0 0 12px" }}>
            {tplAtual.descricao}
          </p>
        )}

        <label className="label">Finalidade *</label>
        <input
          className="input"
          placeholder="Ex.: para apresentação ao INSS · para escola · para retorno ao trabalho"
          value={finalidade}
          onChange={(e) => setFinalidade(e.target.value)}
          disabled={!!busy}
        />

        {REQUER_DEST.has(tipo) && (
          <>
            <div style={{ height: 8 }} />
            <label className="label">Destinatário</label>
            <input
              className="input"
              placeholder="Ex.: Dr. Carlos, psiquiatra · CAPS Vila Mariana"
              value={destinatario}
              onChange={(e) => setDestinatario(e.target.value)}
              disabled={!!busy}
            />
          </>
        )}

        <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 16 }}>
          <Button variant="primary" onClick={gerar} disabled={!!busy}>
            <FileSignature size={16} /> {busy || "Gerar rascunho"}
          </Button>
        </div>
      </Card>
    </div>
  );
}
