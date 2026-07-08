"use client";

import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { ShieldAlert, X } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Segmented } from "@/components/ui/Segmented";
import { StatusBadge } from "@/components/ui/StatusBadge";

type ItemCssrs = { id: string; grupo: string; texto: string };
type OpcaoQuando = { valor: string; rotulo: string };
type PassoPlano = { id: string; titulo: string; ajuda: string };
type Definicao = {
  cssrs: { titulo: string; fonte: string; itens: ItemCssrs[]; comportamento_quando: OpcaoQuando[] };
  plano_seguranca: { titulo: string; passos: PassoPlano[] };
};

/** Espelho do servidor (app/risco/scoring.py) apenas para PRÉVIA — o nível
 *  gravado é sempre derivado no backend. */
function estratificarPrevia(
  resp: Record<string, boolean>,
  comportamento: string,
): "minimo" | "baixo" | "moderado" | "alto" {
  if (resp.q4 || resp.q5 || comportamento === "recente") return "alto";
  if (resp.q3) return "moderado";
  if (resp.q1 || resp.q2 || comportamento === "vida") return "baixo";
  return "minimo";
}

export function RiscoModal({
  pacienteId,
  onClose,
  onSaved,
}: {
  pacienteId: string;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [def, setDef] = useState<Definicao | null>(null);
  const [busy, setBusy] = useState(false);
  const [resp, setResp] = useState<Record<string, boolean>>({});
  const [comportamento, setComportamento] = useState("nao");
  const [plano, setPlano] = useState<Record<string, string>>({});
  const [observacoes, setObservacoes] = useState("");

  useEffect(() => {
    (async () => {
      try {
        setDef(await api<Definicao>("/risco/definicao"));
      } catch (err) {
        toast.error(err instanceof ApiError ? err.message : "Falha ao carregar o rastreio");
        onClose();
      }
    })();
  }, []);

  const nivelPrevia = useMemo(() => estratificarPrevia(resp, comportamento), [resp, comportamento]);

  async function salvar() {
    setBusy(true);
    try {
      await api(`/pacientes/${pacienteId}/avaliacoes-risco`, {
        method: "POST",
        body: JSON.stringify({
          cssrs: {
            q1: !!resp.q1, q2: !!resp.q2, q3: !!resp.q3,
            q4: !!resp.q4, q5: !!resp.q5, q6: !!resp.q6,
            comportamento_quando: comportamento || "nao",
          },
          plano_seguranca: plano,
          observacoes: observacoes.trim() || null,
        }),
      });
      toast.success("Avaliação de risco registrada");
      onSaved();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Falha ao salvar");
      setBusy(false);
    }
  }

  return (
    <Modal open maxWidth={640} busy={busy} onClose={onClose}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <h3 style={{ margin: 0, display: "flex", alignItems: "center", gap: 8 }}>
          <ShieldAlert size={18} color="var(--danger)" /> Avaliação de risco
        </h3>
        <Button onClick={onClose} disabled={busy}><X size={14} /></Button>
      </div>

      <p style={{ color: "var(--muted)", fontSize: 12, marginTop: 4 }}>
        Rastreio de apoio à decisão clínica (C-SSRS). Não é diagnóstico nem substitui
        o seu julgamento; o Práxis não faz alerta ou monitoramento automático.
      </p>

      {def === null ? (
        <p style={{ color: "var(--muted)", fontSize: 13 }}>Carregando…</p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 18, maxHeight: "62vh", overflowY: "auto", paddingRight: 4 }}>
          {/* C-SSRS */}
          <section>
            <div className="label" style={{ marginBottom: 8 }}>{def.cssrs.titulo}</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {def.cssrs.itens.map((it) => (
                <div key={it.id} style={{ display: "flex", gap: 10, alignItems: "flex-start", justifyContent: "space-between" }}>
                  <span style={{ fontSize: 13, flex: 1 }}>{it.texto}</span>
                  <div style={{ flexShrink: 0 }}>
                    <Segmented<"nao" | "sim">
                      label={it.texto}
                      value={resp[it.id] ? "sim" : "nao"}
                      options={[{ value: "nao", label: "Não" }, { value: "sim", label: "Sim" }]}
                      onChange={(v) => setResp((c) => ({ ...c, [it.id]: v === "sim" }))}
                    />
                  </div>
                </div>
              ))}
              {resp.q6 && (
                <label style={{ fontSize: 13, marginTop: 4 }}>
                  Quando ocorreu o comportamento?
                  <select
                    className="input"
                    style={{ marginTop: 4 }}
                    value={comportamento}
                    onChange={(e) => setComportamento(e.target.value)}
                  >
                    {def.cssrs.comportamento_quando.map((o) => (
                      <option key={o.valor} value={o.valor}>{o.rotulo}</option>
                    ))}
                  </select>
                </label>
              )}
            </div>
            <div style={{ marginTop: 10, display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ fontSize: 12, color: "var(--muted)" }}>Nível (prévia):</span>
              <StatusBadge status={`risco_${nivelPrevia}`} />
            </div>
            <p style={{ fontSize: 11, color: "var(--muted)", marginTop: 4 }}>
              Fonte: {def.cssrs.fonte}
            </p>
          </section>

          {/* Plano de Segurança */}
          <section>
            <div className="label" style={{ marginBottom: 8 }}>{def.plano_seguranca.titulo}</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {def.plano_seguranca.passos.map((p) => (
                <div key={p.id}>
                  <label htmlFor={`plano-${p.id}`} style={{ fontSize: 13, fontWeight: 600 }}>{p.titulo}</label>
                  <div style={{ fontSize: 11, color: "var(--muted)", margin: "2px 0 4px" }}>{p.ajuda}</div>
                  <textarea
                    id={`plano-${p.id}`}
                    className="input"
                    rows={2}
                    value={plano[p.id] || ""}
                    onChange={(e) => setPlano((v) => ({ ...v, [p.id]: e.target.value }))}
                  />
                </div>
              ))}
            </div>
          </section>

          <section>
            <label htmlFor="risco-obs" className="label">Observações (opcional)</label>
            <textarea
              id="risco-obs"
              className="input"
              rows={2}
              value={observacoes}
              onChange={(e) => setObservacoes(e.target.value)}
            />
          </section>
        </div>
      )}

      <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 12 }}>
        <Button onClick={onClose} disabled={busy}>Cancelar</Button>
        <Button variant="primary" onClick={salvar} loading={busy} disabled={def === null}>
          Registrar avaliação
        </Button>
      </div>
    </Modal>
  );
}
