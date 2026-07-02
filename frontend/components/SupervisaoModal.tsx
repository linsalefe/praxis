"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Compass, PenLine, Users2, X } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";

type Paciente = { id: string; nome: string };

export function SupervisaoModal({
  onClose, onCreated,
}: {
  onClose: () => void;
  onCreated: () => void;
}) {
  const router = useRouter();
  const [tab, setTab] = useState<"paciente" | "avulso">("avulso");
  const [pacientes, setPacientes] = useState<Paciente[]>([]);
  const [pacienteId, setPacienteId] = useState("");
  const [texto, setTexto] = useState("");
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        setPacientes(await api<Paciente[]>("/pacientes"));
      } catch (err) {
        // silêncio: se falhar, aba avulso ainda funciona
      }
    })();
  }, []);

  async function enviar() {
    if (tab === "paciente" && !pacienteId) return toast.error("Escolha um paciente.");
    if (tab === "avulso" && texto.trim().length < 30) return toast.error("Cole ao menos 30 caracteres.");
    setBusy("Analisando…");
    try {
      const body =
        tab === "paciente"
          ? { paciente_id: pacienteId }
          : { caso_texto: texto };
      const r = await api<{ id: string }>("/supervisao/analisar", {
        method: "POST", body: JSON.stringify(body),
      });
      onCreated();
      router.push(`/supervisao/${r.id}`);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Falha ao analisar");
      setBusy(null);
    }
  }

  return (
    <Modal open maxWidth={620} busy={!!busy} onClose={onClose}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <h3 style={{ margin: 0, display: "flex", alignItems: "center", gap: 8 }}>
            <Compass size={18} color="var(--brand-2)" /> Novo estudo
          </h3>
          <Button onClick={onClose} disabled={!!busy}><X size={14} /></Button>
        </div>
        <p style={{ color: "var(--muted)", fontSize: 13 }}>
          Escolha a origem do caso. O modo avulso não persiste o texto original — só a análise.
        </p>

        <div style={{ display: "flex", gap: 6, borderBottom: "1px solid var(--border)" }}>
          {([
            ["avulso", <><PenLine key="i" size={14} /> Caso avulso</>],
            ["paciente", <><Users2 key="i" size={14} /> Paciente do prontuário</>],
          ] as [typeof tab, React.ReactNode][]).map(([k, lab]) => (
            <button
              key={k}
              type="button"
              onClick={() => setTab(k)}
              disabled={!!busy}
              style={{
                background: "transparent", border: 0,
                color: tab === k ? "var(--brand-2)" : "var(--muted)",
                padding: "8px 12px", cursor: "pointer",
                borderBottom: `2px solid ${tab === k ? "var(--brand-2)" : "transparent"}`,
                display: "inline-flex", alignItems: "center", gap: 6, fontSize: 14,
              }}
            >
              {lab}
            </button>
          ))}
        </div>

        <div style={{ marginTop: 14 }}>
          {tab === "avulso" && (
            <>
              <label className="label">Descrição do caso (anonimizada)</label>
              <p style={{ color: "var(--muted)", fontSize: 12, margin: "0 0 8px" }}>
                Não coloque nomes/documentos identificáveis. Descreva contexto, queixa,
                movimento clínico, dúvidas. Mínimo 30 caracteres.
              </p>
              <textarea
                className="input"
                rows={10}
                placeholder="Ex.: adulta, 34 anos, em atendimento há 4 meses. Queixa de vozes desde adolescência…"
                value={texto}
                onChange={(e) => setTexto(e.target.value)}
                disabled={!!busy}
              />
            </>
          )}

          {tab === "paciente" && (
            <>
              <label className="label">Paciente</label>
              <select
                className="input"
                value={pacienteId}
                onChange={(e) => setPacienteId(e.target.value)}
                disabled={!!busy}
              >
                <option value="">— escolha —</option>
                {pacientes.map((p) => (
                  <option key={p.id} value={p.id}>{p.nome}</option>
                ))}
              </select>
              <p style={{ color: "var(--muted)", fontSize: 12, marginTop: 8 }}>
                Requer consentimento LGPD (tratamento_dados). Nome do paciente
                não vai à IA — apenas o retrato clínico anonimizado.
              </p>
            </>
          )}
        </div>

        <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 16 }}>
          <Button variant="primary" onClick={enviar} disabled={!!busy}>
            <Compass size={16} /> {busy || "Analisar"}
          </Button>
        </div>
    </Modal>
  );
}
