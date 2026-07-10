"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { HeartHandshake, X } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";

type Opcao = { valor: string; rotulo: string };
type Passo = { id: string; titulo: string; ajuda: string };
type Definicao = {
  titulo: string;
  fonte: string;
  vinculos_perda: Opcao[];
  status: Opcao[];
  passos: Passo[];
};

export type PosvencaoDetalhe = {
  id: string;
  ocorrido_em: string;
  vinculo_perda: string;
  status: string;
  plano_posvencao: Record<string, string>;
  observacoes: string | null;
};

/** Cria (sem `registro`) ou edita (com `registro`) um registro de posvenção. */
export function PosvencaoModal({
  pacienteId,
  registro,
  onClose,
  onSaved,
}: {
  pacienteId: string;
  registro?: PosvencaoDetalhe | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const editando = !!registro;
  const [def, setDef] = useState<Definicao | null>(null);
  const [busy, setBusy] = useState(false);
  const [ocorridoEm, setOcorridoEm] = useState(registro?.ocorrido_em ?? "");
  const [vinculo, setVinculo] = useState(registro?.vinculo_perda ?? "familiar");
  const [status, setStatus] = useState(registro?.status ?? "aberto");
  const [plano, setPlano] = useState<Record<string, string>>(registro?.plano_posvencao ?? {});
  const [observacoes, setObservacoes] = useState(registro?.observacoes ?? "");

  useEffect(() => {
    (async () => {
      try {
        setDef(await api<Definicao>("/posvencao/definicao"));
      } catch (err) {
        toast.error(err instanceof ApiError ? err.message : "Falha ao carregar o protocolo");
        onClose();
      }
    })();
  }, []);

  async function salvar() {
    if (!ocorridoEm) {
      toast.error("Informe a data do óbito");
      return;
    }
    setBusy(true);
    const payload = {
      ocorrido_em: ocorridoEm,
      vinculo_perda: vinculo,
      status,
      plano_posvencao: plano,
      observacoes: observacoes.trim() || null,
    };
    try {
      if (editando) {
        await api(`/posvencao/${registro!.id}`, { method: "PATCH", body: JSON.stringify(payload) });
      } else {
        await api(`/pacientes/${pacienteId}/posvencao`, { method: "POST", body: JSON.stringify(payload) });
      }
      toast.success(editando ? "Posvenção atualizada" : "Posvenção registrada");
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
          <HeartHandshake size={18} color="var(--accent)" /> {editando ? "Posvenção" : "Registrar posvenção"}
        </h3>
        <Button onClick={onClose} disabled={busy}><X size={14} /></Button>
      </div>

      <p style={{ color: "var(--muted)", fontSize: 12, marginTop: 4 }}>
        Cuidado após uma morte por suicídio: acolhimento dos enlutados, comunicação segura
        e acompanhamento. Registro de apoio à decisão clínica — não substitui seu julgamento;
        o Práxis não faz alerta ou monitoramento automático.
      </p>

      {def === null ? (
        <p style={{ color: "var(--muted)", fontSize: 13 }}>Carregando…</p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 18, maxHeight: "62vh", overflowY: "auto", paddingRight: 4 }}>
          <section style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            <label style={{ fontSize: 13, flex: "1 1 160px" }}>
              Data do óbito
              <input
                className="input"
                type="date"
                style={{ marginTop: 4 }}
                value={ocorridoEm}
                onChange={(e) => setOcorridoEm(e.target.value)}
              />
            </label>
            <label style={{ fontSize: 13, flex: "1 1 180px" }}>
              Vínculo com o paciente
              <select className="input" style={{ marginTop: 4 }} value={vinculo} onChange={(e) => setVinculo(e.target.value)}>
                {def.vinculos_perda.map((o) => (
                  <option key={o.valor} value={o.valor}>{o.rotulo}</option>
                ))}
              </select>
            </label>
            <label style={{ fontSize: 13, flex: "1 1 160px" }}>
              Andamento
              <select className="input" style={{ marginTop: 4 }} value={status} onChange={(e) => setStatus(e.target.value)}>
                {def.status.map((o) => (
                  <option key={o.valor} value={o.valor}>{o.rotulo}</option>
                ))}
              </select>
            </label>
          </section>

          {/* Protocolo de posvenção */}
          <section>
            <div className="label" style={{ marginBottom: 8 }}>Protocolo de posvenção</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {def.passos.map((p) => (
                <div key={p.id}>
                  <label htmlFor={`posv-${p.id}`} style={{ fontSize: 13, fontWeight: 600 }}>{p.titulo}</label>
                  <div style={{ fontSize: 11, color: "var(--muted)", margin: "2px 0 4px" }}>{p.ajuda}</div>
                  <textarea
                    id={`posv-${p.id}`}
                    className="input"
                    rows={2}
                    value={plano[p.id] || ""}
                    onChange={(e) => setPlano((v) => ({ ...v, [p.id]: e.target.value }))}
                  />
                </div>
              ))}
            </div>
            <p style={{ fontSize: 11, color: "var(--muted)", marginTop: 8 }}>Fonte: {def.fonte}</p>
          </section>

          <section>
            <label htmlFor="posv-obs" className="label">Observações (opcional)</label>
            <textarea
              id="posv-obs"
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
          {editando ? "Salvar" : "Registrar posvenção"}
        </Button>
      </div>
    </Modal>
  );
}
