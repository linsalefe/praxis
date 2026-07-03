"use client";

import { useEffect, useRef, useState, use } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { CheckCircle2, Save } from "lucide-react";
import { api, ApiError, getToken } from "@/lib/api";
import { Topbar } from "@/components/Topbar";
import { CopiarBtn } from "@/components/ui/CopiarBtn";
import { BreadcrumbPaciente } from "@/components/ui/BreadcrumbPaciente";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";

type Evolucao = {
  id: string; sessao_id: string; paciente_id: string | null; autor_id: string;
  identificacao: string | null; demanda_objetivos: string | null;
  evolucao: string | null; encaminhamento: string | null;
  assinado_em: string | null; hash_assinatura: string | null;
};

const BLOCOS: Array<[keyof Evolucao, string, string]> = [
  ["identificacao", "Identificação", "Dados de identificação e contexto do atendimento."],
  ["demanda_objetivos", "Avaliação de demanda / objetivos", "Demanda apresentada e objetivos terapêuticos combinados."],
  ["evolucao", "Evolução", "Descrição da sessão, hipóteses, movimento clínico."],
  ["encaminhamento", "Encaminhamento / encerramento", "Ações combinadas, encaminhamentos, notas de encerramento."],
];

export default function EvolucaoPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const [ev, setEv] = useState<Evolucao | null>(null);
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [signing, setSigning] = useState(false);
  const [lastSaved, setLastSaved] = useState<Date | null>(null);
  const [confirmAssinar, setConfirmAssinar] = useState(false);
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  // Referência sempre atualizada — o autosave debounced lê daqui, não de um
  // closure antigo, então nenhuma tecla final se perde.
  const evRef = useRef<Evolucao | null>(ev);
  evRef.current = ev;

  useEffect(() => {
    if (!getToken()) return void router.replace("/login");
    (async () => {
      try { setEv(await api<Evolucao>(`/evolucoes/${id}`)); }
      catch (err) {
        if (err instanceof ApiError && err.status === 401) router.replace("/login");
        else toast.error(err instanceof ApiError ? err.message : "Erro");
      }
    })();
  }, [id, router]);

  // Limpa timer pendente ao desmontar.
  useEffect(() => () => { if (saveTimer.current) clearTimeout(saveTimer.current); }, []);

  // Guarda de saída: enquanto houver texto não salvo, o navegador confirma antes de sair.
  useEffect(() => {
    if (!dirty) return;
    const h = (e: BeforeUnloadEvent) => { e.preventDefault(); e.returnValue = ""; };
    window.addEventListener("beforeunload", h);
    return () => window.removeEventListener("beforeunload", h);
  }, [dirty]);

  function upd(k: keyof Evolucao, v: string) {
    if (!ev || ev.assinado_em) return;
    setEv({ ...ev, [k]: v });
    setDirty(true);
    scheduleSave();
  }

  const scheduleSave = () => {
    if (saveTimer.current) clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(() => salvar({ silent: true }), 800);
  };

  async function salvar({ silent = false }: { silent?: boolean } = {}) {
    const cur = evRef.current;
    if (!cur || cur.assinado_em) return;
    if (saveTimer.current) { clearTimeout(saveTimer.current); saveTimer.current = null; }
    setSaving(true);
    try {
      const patched = await api<Evolucao>(`/evolucoes/${id}`, {
        method: "PATCH",
        body: JSON.stringify({
          identificacao: cur.identificacao,
          demanda_objetivos: cur.demanda_objetivos,
          evolucao: cur.evolucao,
          encaminhamento: cur.encaminhamento,
        }),
      });
      setEv(patched);
      setDirty(false);
      setLastSaved(new Date());
      if (!silent) toast.success("Rascunho salvo.");
    } catch (err) {
      if (!silent) toast.error(err instanceof ApiError ? err.message : "Falha");
    } finally {
      setSaving(false);
    }
  }

  async function assinar() {
    if (!evRef.current) return;
    if (dirty) await salvar({ silent: true });
    setSigning(true);
    try {
      const signed = await api<Evolucao>(`/evolucoes/${id}/assinar`, { method: "POST" });
      setEv(signed);
      setConfirmAssinar(false);
      toast.success("Evolução assinada.");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Falha");
    } finally {
      setSigning(false);
    }
  }

  if (!ev) return (<><Topbar /><main className="container-praxis"><p style={{ color: "var(--muted)" }}>Carregando…</p></main></>);

  const assinada = !!ev.assinado_em;

  return (
    <>
      <Topbar />
      <main className="container-praxis" style={{ maxWidth: 820 }}>
        <BreadcrumbPaciente pacienteId={ev.paciente_id} />
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <h1 style={{ fontSize: 22, margin: "8px 0" }}>Evolução clínica</h1>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <CopiarBtn
              className="btn btn-ghost"
              texto={BLOCOS.map(([k, titulo]) => `${titulo}\n${(ev[k] as string) || ""}`).join("\n\n")}
            />
            {assinada ? (
              <span className="badge" style={{ color: "var(--ok)" }}>
                Assinada em {new Date(ev.assinado_em!).toLocaleString("pt-BR")}
              </span>
            ) : (
              <span className="badge" style={{ color: "var(--muted)" }}>
                {saving ? (
                  "salvando…"
                ) : dirty ? (
                  "Rascunho · editando…"
                ) : lastSaved ? (
                  <span style={{ fontFamily: "var(--font-mono)" }}>
                    salvo às {lastSaved.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}
                  </span>
                ) : (
                  "Rascunho"
                )}
              </span>
            )}
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 16, marginTop: 16 }}>
          {BLOCOS.map(([k, titulo, hint]) => (
            <Card key={k}>
              <label className="label" style={{ fontSize: 14, color: "var(--text)", marginBottom: 4 }}>{titulo}</label>
              <p style={{ margin: "0 0 8px", color: "var(--muted)", fontSize: 12 }}>{hint}</p>
              <textarea
                className="input"
                rows={5}
                disabled={assinada}
                value={(ev[k] as string) || ""}
                onChange={(e) => upd(k, e.target.value)}
              />
            </Card>
          ))}
        </div>

        <div style={{ display: "flex", gap: 12, marginTop: 20 }}>
          <Button onClick={() => salvar()} loading={saving} disabled={assinada || !dirty}>
            <Save size={16} /> {saving ? "Salvando…" : "Salvar rascunho"}
          </Button>
          <Button variant="primary" onClick={() => setConfirmAssinar(true)} loading={signing} disabled={assinada}>
            <CheckCircle2 size={16} /> {signing ? "Assinando…" : "Assinar evolução"}
          </Button>
        </div>

        {assinada && ev.hash_assinatura && (
          <p style={{ marginTop: 16, color: "var(--muted)", fontFamily: "monospace", fontSize: 12 }}>
            SHA-256: {ev.hash_assinatura}
          </p>
        )}
      </main>

      <ConfirmDialog
        open={confirmAssinar}
        title="Assinar evolução"
        description="Após assinar, o conteúdo fica imutável, recebe hash de integridade e passa a compor o prontuário. Revise o texto antes de confirmar."
        confirmLabel="Assinar"
        cancelLabel="Continuar revisando"
        confirmVariant="primary"
        busy={signing}
        busyLabel="Assinando…"
        onConfirm={assinar}
        onCancel={() => setConfirmAssinar(false)}
      />
    </>
  );
}
