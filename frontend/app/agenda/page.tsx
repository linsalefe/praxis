"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import { CalendarPlus, ChevronLeft, ChevronRight, Clock, Video } from "lucide-react";
import { api, ApiError, getToken } from "@/lib/api";
import { Topbar } from "@/components/Topbar";
import { Skeleton } from "@/components/ui/Skeleton";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { Drawer } from "@/components/ui/Drawer";
import { TelessessaoModal } from "@/components/TelessessaoModal";

type Sessao = {
  id: string; paciente_id: string; paciente_nome: string;
  data: string; modalidade: string; status: string;
};
type PacienteLite = { id: string; nome: string };

const STATUS_BADGE: Record<string, string> = {
  agendada: "badge-info", realizada: "badge-pos", falta: "badge-warn", cancelada: "badge-neutral",
};
const STATUS_LABEL: Record<string, string> = {
  agendada: "agendada", realizada: "realizada", falta: "falta", cancelada: "cancelada",
};

// --- helpers de data (locais, sem UTC surpresa) ---
const p2 = (n: number) => String(n).padStart(2, "0");
const ymd = (d: Date) => `${d.getFullYear()}-${p2(d.getMonth() + 1)}-${p2(d.getDate())}`;
const addDays = (d: Date, n: number) => { const x = new Date(d); x.setDate(x.getDate() + n); return x; };
function weekStart(d: Date) { const off = (d.getDay() + 6) % 7; return addDays(d, -off); } // segunda
const toLocalInput = (d: Date) => `${ymd(d)}T${p2(d.getHours())}:${p2(d.getMinutes())}`;
const hora = (iso: string) => new Date(iso).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
const diaLongo = (d: Date) => d.toLocaleDateString("pt-BR", { weekday: "short", day: "2-digit", month: "2-digit" });

export default function AgendaPage() {
  const router = useRouter();
  const [view, setView] = useState<"dia" | "semana">("semana");
  const [anchor, setAnchor] = useState<Date>(() => new Date());
  const [sessoes, setSessoes] = useState<Sessao[]>([]);
  const [loading, setLoading] = useState(true);
  const [pacientes, setPacientes] = useState<PacienteLite[]>([]);
  const [drawer, setDrawer] = useState<{ open: boolean; editar?: Sessao }>({ open: false });
  const [cancelar, setCancelar] = useState<Sessao | null>(null);
  const [telessessao, setTelessessao] = useState<Sessao | null>(null);

  const range = useMemo(() => {
    if (view === "dia") return { de: ymd(anchor), ate: ymd(anchor) };
    const s = weekStart(anchor);
    return { de: ymd(s), ate: ymd(addDays(s, 6)) };
  }, [view, anchor]);

  const carregar = useCallback(async () => {
    setLoading(true);
    try {
      setSessoes(await api<Sessao[]>(`/sessoes/agenda?de=${range.de}&ate=${range.ate}`));
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) router.replace("/login");
      else toast.error(err instanceof ApiError ? err.message : "Erro ao carregar agenda");
    } finally {
      setLoading(false);
    }
  }, [range.de, range.ate, router]);

  useEffect(() => {
    if (!getToken()) return void router.replace("/login");
    carregar();
  }, [carregar, router]);

  useEffect(() => {
    api<PacienteLite[]>("/pacientes").then(setPacientes).catch(() => { /* seletor degrada p/ vazio */ });
  }, []);

  const passo = view === "dia" ? 1 : 7;

  async function mudarStatus(s: Sessao, status: string) {
    try {
      await api(`/sessoes/${s.id}`, { method: "PATCH", body: JSON.stringify({ status }) });
      toast.success(`Sessão marcada como ${STATUS_LABEL[status]}.`);
      carregar();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Falha ao atualizar");
    }
  }

  const dias = useMemo(() => {
    if (view === "dia") return [anchor];
    const s = weekStart(anchor);
    return Array.from({ length: 7 }, (_, i) => addDays(s, i));
  }, [view, anchor]);

  const porDia = useMemo(() => {
    const m = new Map<string, Sessao[]>();
    for (const s of sessoes) {
      const k = ymd(new Date(s.data));
      (m.get(k) ?? m.set(k, []).get(k)!).push(s);
    }
    return m;
  }, [sessoes]);

  return (
    <>
      <Topbar />
      <main className="container-praxis" style={{ maxWidth: 860 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
          <h1 style={{ fontSize: 20, margin: 0 }}>Agenda</h1>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <div className="badge" style={{ padding: 0, overflow: "hidden", display: "inline-flex" }}>
              {(["dia", "semana"] as const).map((v) => (
                <button key={v} onClick={() => setView(v)}
                  style={{
                    border: "none", padding: "6px 12px", cursor: "pointer", textTransform: "capitalize",
                    background: view === v ? "var(--teal-100)" : "transparent",
                    color: view === v ? "var(--teal-700)" : "var(--muted)", fontWeight: view === v ? 600 : 400,
                  }}>{v}</button>
              ))}
            </div>
            <button className="btn btn-primary" onClick={() => setDrawer({ open: true })}>
              <CalendarPlus size={16} /> Nova sessão
            </button>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", margin: "14px 0" }}>
          <button className="btn" onClick={() => setAnchor((d) => addDays(d, -passo))} aria-label="Anterior">
            <ChevronLeft size={16} /> Anterior
          </button>
          <div style={{ textAlign: "center" }}>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 13 }}>
              {view === "dia"
                ? anchor.toLocaleDateString("pt-BR", { weekday: "long", day: "2-digit", month: "long", year: "numeric" })
                : `${diaLongo(weekStart(anchor))} — ${diaLongo(addDays(weekStart(anchor), 6))}`}
            </div>
            <button className="link" style={{ fontSize: 12 }} onClick={() => setAnchor(new Date())}>hoje</button>
          </div>
          <button className="btn" onClick={() => setAnchor((d) => addDays(d, passo))} aria-label="Próxima">
            Próxima <ChevronRight size={16} />
          </button>
        </div>

        {loading ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <Skeleton height={64} radius="var(--radius-lg)" />
            <Skeleton height={64} radius="var(--radius-lg)" />
            <Skeleton height={64} radius="var(--radius-lg)" />
          </div>
        ) : sessoes.length === 0 ? (
          <div className="card" style={{ textAlign: "center", color: "var(--muted)", padding: 28 }}>
            {view === "dia" ? "Nenhuma sessão neste dia." : "Nenhuma sessão nesta semana."}
            <div style={{ marginTop: 10 }}>
              <button className="btn" onClick={() => setDrawer({ open: true })}><CalendarPlus size={15} /> Agendar</button>
            </div>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: view === "dia" ? 8 : 18 }}>
            {dias.map((d) => {
              const lista = porDia.get(ymd(d)) ?? [];
              if (view === "semana" && lista.length === 0) {
                return (
                  <div key={ymd(d)}>
                    <div style={{ fontFamily: "var(--font-display)", fontWeight: 500, textTransform: "capitalize", marginBottom: 6 }}>{diaLongo(d)}</div>
                    <div style={{ color: "var(--muted)", fontSize: 13, paddingLeft: 2 }}>sem sessões</div>
                  </div>
                );
              }
              return (
                <div key={ymd(d)}>
                  {view === "semana" && (
                    <div style={{ fontFamily: "var(--font-display)", fontWeight: 500, textTransform: "capitalize", marginBottom: 6 }}>{diaLongo(d)}</div>
                  )}
                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    {lista.map((s) => (
                      <SessaoRow key={s.id} s={s} onStatus={mudarStatus}
                        onReagendar={() => setDrawer({ open: true, editar: s })}
                        onCancelar={() => setCancelar(s)}
                        onSala={() => setTelessessao(s)} />
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </main>

      <Drawer
        open={drawer.open}
        title={drawer.editar ? "Reagendar sessão" : "Nova sessão"}
        onClose={() => setDrawer({ open: false })}
      >
        <SessaoForm
          editar={drawer.editar}
          pacientes={pacientes}
          anchor={anchor}
          onSalvo={() => { setDrawer({ open: false }); carregar(); }}
        />
      </Drawer>

      <ConfirmDialog
        open={!!cancelar}
        title="Cancelar sessão"
        description={cancelar ? `A sessão de ${cancelar.paciente_nome} em ${new Date(cancelar.data).toLocaleString("pt-BR")} será marcada como cancelada.` : ""}
        confirmLabel="Cancelar sessão"
        onConfirm={() => { if (cancelar) mudarStatus(cancelar, "cancelada"); setCancelar(null); }}
        onCancel={() => setCancelar(null)}
      />

      {telessessao && (
        <TelessessaoModal
          sessaoId={telessessao.id}
          pacienteId={telessessao.paciente_id}
          pacienteNome={telessessao.paciente_nome}
          onClose={() => setTelessessao(null)}
        />
      )}
    </>
  );
}

function SessaoRow({
  s, onStatus, onReagendar, onCancelar, onSala,
}: {
  s: Sessao;
  onStatus: (s: Sessao, status: string) => void;
  onReagendar: () => void;
  onCancelar: () => void;
  onSala: () => void;
}) {
  const pendente = s.status === "agendada" && new Date(s.data) < new Date();
  return (
    <div className="card" style={{
      display: "flex", alignItems: "center", gap: 12, padding: "12px 14px",
      borderLeft: pendente ? "3px solid var(--warn-line)" : undefined,
    }}>
      <div style={{ fontFamily: "var(--font-mono)", fontSize: 15, minWidth: 52, display: "flex", alignItems: "center", gap: 4 }}>
        <Clock size={13} color="var(--muted)" /> {hora(s.data)}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <Link href={`/pacientes/${s.paciente_id}`} className="link" style={{ fontWeight: 500 }}>{s.paciente_nome}</Link>
        <div style={{ display: "flex", gap: 6, alignItems: "center", marginTop: 2 }}>
          <span className="badge">{s.modalidade}</span>
          <span className={`badge ${STATUS_BADGE[s.status] ?? ""}`}>{STATUS_LABEL[s.status] ?? s.status}</span>
          {pendente && <span style={{ fontSize: 11, color: "var(--warn-fg)", fontFamily: "var(--font-mono)" }}>pendente de baixa</span>}
        </div>
      </div>
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", justifyContent: "flex-end" }}>
        {s.modalidade === "online" && s.status !== "cancelada" && (
          <button className="btn btn-primary" onClick={onSala} title="Telessessão"><Video size={15} /> Sala</button>
        )}
        {s.status === "agendada" ? (
          <>
            <button className="btn" onClick={() => onStatus(s, "realizada")} title="Marcar comparecido">Realizada</button>
            <button className="btn" onClick={() => onStatus(s, "falta")}>Falta</button>
            <button className="btn btn-danger" onClick={onCancelar}>Cancelar</button>
          </>
        ) : (
          <button className="btn" onClick={() => onStatus(s, "agendada")}>Reabrir</button>
        )}
        <button className="btn" onClick={onReagendar}>Reagendar</button>
      </div>
    </div>
  );
}

function SessaoForm({
  editar, pacientes, anchor, onSalvo,
}: {
  editar?: Sessao;
  pacientes: PacienteLite[];
  anchor: Date;
  onSalvo: () => void;
}) {
  const [pacienteId, setPacienteId] = useState(editar?.paciente_id ?? "");
  const [data, setData] = useState(() => toLocalInput(editar ? new Date(editar.data) : anchor));
  const [modalidade, setModalidade] = useState(editar?.modalidade ?? "presencial");
  const [busy, setBusy] = useState(false);

  async function salvar(e: React.FormEvent) {
    e.preventDefault();
    if (!editar && !pacienteId) { toast.error("Escolha o paciente."); return; }
    if (!data) { toast.error("Informe data e hora."); return; }
    setBusy(true);
    try {
      const iso = new Date(data).toISOString();
      if (editar) {
        await api(`/sessoes/${editar.id}`, { method: "PATCH", body: JSON.stringify({ data: iso, modalidade }) });
        toast.success("Sessão reagendada.");
      } else {
        await api("/sessoes", { method: "POST", body: JSON.stringify({ paciente_id: pacienteId, data: iso, modalidade, status: "agendada" }) });
        toast.success("Sessão agendada.");
      }
      onSalvo();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Falha ao salvar");
      setBusy(false);
    }
  }

  return (
    <form onSubmit={salvar} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <div>
        <label className="label">Paciente</label>
        {editar ? (
          <input className="input" value={editar.paciente_nome} disabled />
        ) : (
          <select className="input" value={pacienteId} onChange={(e) => setPacienteId(e.target.value)} required>
            <option value="">Selecione…</option>
            {pacientes.map((p) => <option key={p.id} value={p.id}>{p.nome}</option>)}
          </select>
        )}
      </div>
      <div>
        <label className="label">Data e hora</label>
        <input className="input" type="datetime-local" value={data} onChange={(e) => setData(e.target.value)} required />
      </div>
      <div>
        <label className="label">Modalidade</label>
        <select className="input" value={modalidade} onChange={(e) => setModalidade(e.target.value)}>
          <option value="presencial">Presencial</option>
          <option value="online">Online</option>
        </select>
      </div>
      <button className="btn btn-primary" disabled={busy} style={{ marginTop: 4 }}>
        <CalendarPlus size={16} /> {busy ? "Salvando…" : editar ? "Reagendar" : "Agendar"}
      </button>
    </form>
  );
}
