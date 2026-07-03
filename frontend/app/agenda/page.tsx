"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import { Ban, CalendarClock, CalendarPlus, Check, ChevronLeft, ChevronRight, Clock, UserX, Video } from "lucide-react";
import { api, ApiError, getToken } from "@/lib/api";
import { statusLabel, modalidadeLabel } from "@/lib/labels";
import { formatNome } from "@/lib/format";
import { Topbar } from "@/components/Topbar";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Skeleton } from "@/components/ui/Skeleton";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Field } from "@/components/ui/Field";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { MenuAcoes } from "@/components/ui/MenuAcoes";
import { Segmented } from "@/components/ui/Segmented";
import { Drawer } from "@/components/ui/Drawer";
import { TelessessaoModal } from "@/components/TelessessaoModal";

type Sessao = {
  id: string; paciente_id: string; paciente_nome: string;
  data: string; modalidade: string; status: string;
};
type PacienteLite = { id: string; nome: string };

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
  const [drawer, setDrawer] = useState<{ open: boolean; editar?: Sessao; dataInicial?: Date }>({ open: false });
  const [cancelar, setCancelar] = useState<Sessao | null>(null);
  const [telessessao, setTelessessao] = useState<Sessao | null>(null);

  // UX-3 U15: no celular a agenda abre em "dia" por padrão (semana no desktop).
  // Em useEffect (não no initializer) para evitar mismatch de hidratação.
  useEffect(() => {
    if (window.matchMedia("(max-width: 640px)").matches) setView("dia");
  }, []);

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

  // A4: navegação por teclado — ←/→ mudam o período, "t" volta para hoje.
  // Ignora quando há modal aberto ou o foco está num campo de formulário.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (drawer.open || cancelar || telessessao) return;
      const tag = (e.target as HTMLElement | null)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
      if (e.key === "ArrowLeft") setAnchor((d) => addDays(d, -passo));
      else if (e.key === "ArrowRight") setAnchor((d) => addDays(d, passo));
      else if (e.key === "t" || e.key === "T") setAnchor(new Date());
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [passo, drawer.open, cancelar, telessessao]);

  // A2: abre "Nova sessão" com a data pré-preenchida no dia clicado (09:00).
  const novaNoDia = (d: Date) => {
    const dt = new Date(d);
    dt.setHours(9, 0, 0, 0);
    setDrawer({ open: true, dataInicial: dt });
  };
  const ehHoje = (d: Date) => ymd(d) === ymd(new Date());

  async function mudarStatus(s: Sessao, status: string) {
    const anterior = s.status;
    try {
      await api(`/sessoes/${s.id}`, { method: "PATCH", body: JSON.stringify({ status }) });
      toast.success(`Sessão marcada como ${statusLabel(status).toLowerCase()}.`, {
        action: { label: "Desfazer", onClick: () => reverterStatus(s.id, anterior) },
      });
      carregar();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Falha ao atualizar");
    }
  }

  async function reverterStatus(sessaoId: string, status: string) {
    try {
      await api(`/sessoes/${sessaoId}`, { method: "PATCH", body: JSON.stringify({ status }) });
      toast.success(`Alteração desfeita — sessão voltou para ${statusLabel(status).toLowerCase()}.`);
      carregar();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Falha ao desfazer");
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
          <h1 style={{ fontSize: "var(--fs-xl)", margin: 0 }}>Agenda</h1>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <Segmented
              label="Visualização"
              value={view}
              onChange={setView}
              options={[{ value: "dia", label: "Dia" }, { value: "semana", label: "Semana" }]}
            />
            <Button variant="primary" onClick={() => setDrawer({ open: true })}>
              <CalendarPlus size={16} /> Nova sessão
            </Button>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", margin: "14px 0" }}>
          <Button onClick={() => setAnchor((d) => addDays(d, -passo))} aria-label="Anterior">
            <ChevronLeft size={16} /> Anterior
          </Button>
          <div style={{ textAlign: "center" }}>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 13 }}>
              {view === "dia"
                ? anchor.toLocaleDateString("pt-BR", { weekday: "long", day: "2-digit", month: "long", year: "numeric" })
                : `${diaLongo(weekStart(anchor))} — ${diaLongo(addDays(weekStart(anchor), 6))}`}
            </div>
            <button className="link" style={{ fontSize: 12 }} onClick={() => setAnchor(new Date())}>Hoje</button>
          </div>
          <Button onClick={() => setAnchor((d) => addDays(d, passo))} aria-label="Próxima">
            Próxima <ChevronRight size={16} />
          </Button>
        </div>

        {loading ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <Skeleton height={64} radius="var(--radius-lg)" />
            <Skeleton height={64} radius="var(--radius-lg)" />
            <Skeleton height={64} radius="var(--radius-lg)" />
          </div>
        ) : sessoes.length === 0 ? (
          <Card style={{ textAlign: "center", color: "var(--muted)", padding: 28 }}>
            {view === "dia" ? "Nenhuma sessão neste dia." : "Nenhuma sessão nesta semana."}
            <div style={{ marginTop: 10 }}>
              <Button onClick={() => setDrawer({ open: true })}><CalendarPlus size={15} /> Agendar</Button>
            </div>
          </Card>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: view === "dia" ? 8 : 18 }}>
            {dias.map((d) => {
              const lista = porDia.get(ymd(d)) ?? [];
              const hoje = ehHoje(d);
              const Cabecalho = view === "semana" ? (
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                  <div style={{
                    fontFamily: "var(--font-display)", fontWeight: hoje ? 700 : 500,
                    textTransform: "capitalize", color: hoje ? "var(--brand)" : "var(--text)",
                  }}>{diaLongo(d)}</div>
                  {hoje && <span className="badge badge-info">hoje</span>}
                  <button
                    type="button" className="link" onClick={() => novaNoDia(d)}
                    title="Nova sessão neste dia"
                    style={{ marginLeft: "auto", background: "none", border: "none", cursor: "pointer", display: "inline-flex", alignItems: "center", gap: 4, fontSize: 13 }}
                  >
                    <CalendarPlus size={14} /> Nova
                  </button>
                </div>
              ) : null;

              if (view === "semana" && lista.length === 0) {
                return (
                  <div key={ymd(d)} style={hoje ? { background: "var(--surface-2)", borderRadius: "var(--radius-md)", padding: "8px 10px" } : undefined}>
                    {Cabecalho}
                    <button
                      type="button" onClick={() => novaNoDia(d)}
                      style={{ width: "100%", textAlign: "left", background: "none", border: "1px dashed var(--border)", borderRadius: "var(--radius-md)", color: "var(--muted)", fontSize: 13, padding: "10px 12px", cursor: "pointer" }}
                    >
                      sem sessões — clique para agendar
                    </button>
                  </div>
                );
              }
              return (
                <div key={ymd(d)} style={hoje && view === "semana" ? { background: "var(--surface-2)", borderRadius: "var(--radius-md)", padding: "8px 10px" } : undefined}>
                  {Cabecalho}
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
          anchor={drawer.dataInicial ?? anchor}
          onSalvo={() => { setDrawer({ open: false }); carregar(); }}
        />
      </Drawer>

      <ConfirmDialog
        open={!!cancelar}
        title="Cancelar sessão"
        description={cancelar ? `A sessão de ${formatNome(cancelar.paciente_nome)} em ${new Date(cancelar.data).toLocaleString("pt-BR")} será marcada como cancelada.` : ""}
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
    <Card className="row-stack" style={{
      display: "flex", alignItems: "center", gap: 12, padding: "12px 14px",
      borderLeft: pendente ? "3px solid var(--warn-line)" : undefined,
    }}>
      <div style={{ fontFamily: "var(--font-mono)", fontSize: 15, minWidth: 52, display: "flex", alignItems: "center", gap: 4 }}>
        <Clock size={13} color="var(--muted)" /> {hora(s.data)}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <Link href={`/pacientes/${s.paciente_id}`} className="link" style={{ fontWeight: 500 }}>{formatNome(s.paciente_nome)}</Link>
        <div style={{ display: "flex", gap: 6, alignItems: "center", marginTop: 2 }}>
          <span className="badge">{modalidadeLabel(s.modalidade)}</span>
          <StatusBadge status={s.status} />
          {pendente && <span style={{ fontSize: 11, color: "var(--warn-fg)", fontFamily: "var(--font-mono)" }}>pendente de baixa</span>}
        </div>
      </div>
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", justifyContent: "flex-end", alignItems: "center" }}>
        {s.modalidade === "online" && s.status !== "cancelada" && (
          <Button variant="primary" onClick={onSala} title="Telessessão"><Video size={15} /> Sala</Button>
        )}
        {s.status === "agendada" ? (
          <>
            {/* Uma ação de destaque; secundárias e a destrutiva no menu "···". */}
            <Button variant="primary" onClick={() => onStatus(s, "realizada")} title="Marcar comparecido">
              <Check size={15} /> Realizada
            </Button>
            <MenuAcoes
              secundarias={[
                { label: "Marcar falta", icon: <UserX size={16} />, onClick: () => onStatus(s, "falta") },
                { label: "Reagendar", icon: <CalendarClock size={16} />, onClick: onReagendar },
              ]}
              destrutivas={[
                { label: "Cancelar sessão", icon: <Ban size={16} />, onClick: onCancelar },
              ]}
            />
          </>
        ) : (
          <>
            <Button onClick={() => onStatus(s, "agendada")}>Reabrir</Button>
            <MenuAcoes
              secundarias={[
                { label: "Reagendar", icon: <CalendarClock size={16} />, onClick: onReagendar },
              ]}
            />
          </>
        )}
      </div>
    </Card>
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
      <Field label="Paciente">
        {editar ? (
          <input className="input" value={editar.paciente_nome} disabled />
        ) : (
          <select className="input" value={pacienteId} onChange={(e) => setPacienteId(e.target.value)} required>
            <option value="">Selecione…</option>
            {pacientes.map((p) => <option key={p.id} value={p.id}>{formatNome(p.nome)}</option>)}
          </select>
        )}
      </Field>
      <Field label="Data e hora">
        <input className="input" type="datetime-local" value={data} onChange={(e) => setData(e.target.value)} required />
      </Field>
      <Field label="Modalidade">
        <select className="input" value={modalidade} onChange={(e) => setModalidade(e.target.value)}>
          <option value="presencial">Presencial</option>
          <option value="online">Online</option>
        </select>
      </Field>
      <Button variant="primary" loading={busy} style={{ marginTop: 4 }}>
        <CalendarPlus size={16} /> {busy ? "Salvando…" : editar ? "Reagendar" : "Agendar"}
      </Button>
    </form>
  );
}
