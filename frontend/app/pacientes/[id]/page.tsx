"use client";

import { useEffect, useState, use } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import { Activity, CalendarClock, CalendarPlus, ClipboardCheck, ClipboardList, Download, FilePlus, FileSignature, FileText, Package, Paperclip, Trash2, Video } from "lucide-react";
import { api, ApiError, getToken } from "@/lib/api";
import { formatCentavos, reaisParaCentavos } from "@/lib/money";
import { dataRelativa } from "@/lib/date";
import { instrumentoTipoLabel, modalidadeLabel, docTipoLabel } from "@/lib/labels";
import { formatNome } from "@/lib/format";
import { Topbar } from "@/components/Topbar";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { ScribeModal } from "@/components/ScribeModal";
import { TelessessaoModal } from "@/components/TelessessaoModal";
import { ConformidadeIaCard } from "@/components/ConformidadeIaCard";
import { InstrumentoModal } from "@/components/InstrumentoModal";
import { PrepararSessaoModal } from "@/components/PrepararSessaoModal";
import { DocumentoModal } from "@/components/DocumentoModal";
import { SofiaPainelProntuario } from "@/components/SofiaPainelProntuario";
import { PresenceMark } from "@/components/ui/PresenceMark";
import { PacienteCard } from "@/components/ui/PacienteCard";
import { Skeleton } from "@/components/ui/Skeleton";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { Drawer } from "@/components/ui/Drawer";
import { MenuAcoes } from "@/components/ui/MenuAcoes";
import { GraficoTrajetoria, type SerieTrajetoria } from "@/components/ui/GraficoTrajetoria";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { SectionTitle } from "@/components/ui/SectionTitle";
import { Field } from "@/components/ui/Field";

type TabKey = "visao" | "trajetoria" | "sessoes" | "instrumentos" | "documentos";
const TABS: [TabKey, string][] = [
  ["visao", "Visão geral"], ["trajetoria", "Trajetória"], ["sessoes", "Sessões"],
  ["instrumentos", "Instrumentos"], ["documentos", "Documentos"],
];
function normalizarTab(v: string | null): TabKey {
  if (v === "anexos") return "documentos";           // alias do redirect do InstrumentoWizard
  if (v === "geral") return "visao";
  return (TABS.some(([k]) => k === v) ? v : "visao") as TabKey;
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8040";

type Anexo = {
  id: string; titulo: string; mimetype: string; bytes: number;
  sha256: string; criado_em: string; origem_tipo: string;
};
type RespInstr = {
  id: string; instrumento_tipo: string; instrumento_versao: string;
  status: string; finalizado_em: string | null; anexo_id: string | null; criado_em: string;
};
type DocumentoCFP = {
  id: string; tipo: string; finalidade: string; status: string;
  assinado_em: string | null; anexo_pdf_id: string | null; criado_em: string;
};

type Paciente = {
  id: string; nome: string; contato: string | null;
  nascimento: string | null; documento: string | null; sexo: string | null;
};
type Sessao = {
  id: string; paciente_id: string; data: string; modalidade: string; status: string;
  valor_centavos: number | null;
};
type EventoTimeline = {
  data: string; tipo_evento: string; titulo: string; ref_id: string;
  meta: Record<string, unknown>;
};
type Resumo = {
  sessoes: { realizadas: number; faltas: number; canceladas: number; agendadas_futuras: number; total: number };
  adesao: { num: number; den: number; criterio: string };
  evolucoes: { assinadas: number; rascunho: number };
  instrumentos_aplicados: number;
  primeira_sessao: string | null; ultima_sessao: string | null;
};

export default function FichaPacientePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const qs = useSearchParams();
  const [tab, setTab] = useState<TabKey>(() => normalizarTab(qs.get("tab")));
  const novoAnexoId = qs.get("novo");
  const [agendarOpen, setAgendarOpen] = useState(false);
  const [pac, setPac] = useState<Paciente | null>(null);
  const [sessoes, setSessoes] = useState<Sessao[]>([]);
  const [loading, setLoading] = useState(true);
  const [newSes, setNewSes] = useState({ data: "", modalidade: "presencial", status: "agendada", valor: "" });
  const [scribeSessao, setScribeSessao] = useState<string | null>(null);
  const [telessessao, setTelessessao] = useState<string | null>(null);
  const [instrModal, setInstrModal] = useState(false);
  const [prepModal, setPrepModal] = useState(false);
  const [prepContexto, setPrepContexto] = useState<string | null>(null);
  const [sofiaOpen, setSofiaOpen] = useState(false);
  const [docModal, setDocModal] = useState(false);
  const [respostas, setRespostas] = useState<RespInstr[]>([]);
  const [anexos, setAnexos] = useState<Anexo[]>([]);
  const [documentos, setDocumentos] = useState<DocumentoCFP[]>([]);
  const [confirmDel, setConfirmDel] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [confirmExport, setConfirmExport] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [resumo, setResumo] = useState<Resumo | null>(null);
  const [series, setSeries] = useState<SerieTrajetoria[]>([]);
  const [timeline, setTimeline] = useState<EventoTimeline[]>([]);

  useEffect(() => {
    if (!getToken()) return void router.replace("/login");
    (async () => {
      try {
        const p = await api<Paciente>(`/pacientes/${id}`);
        setPac(p);
        try {
          localStorage.setItem("praxis.last_paciente", JSON.stringify({ id: p.id, nome: p.nome }));
        } catch { /* ignora */ }
        setSessoes(await api<Sessao[]>(`/sessoes/paciente/${id}`));
        setRespostas(await api<RespInstr[]>(`/pacientes/${id}/respostas-instrumento`));
        setAnexos(await api<Anexo[]>(`/pacientes/${id}/anexos`));
        setDocumentos(await api<DocumentoCFP[]>(`/pacientes/${id}/documentos`));
        setResumo(await api<Resumo>(`/pacientes/${id}/resumo`));
        setSeries((await api<{ series: SerieTrajetoria[] }>(`/pacientes/${id}/trajetoria`)).series);
        setTimeline((await api<{ eventos: EventoTimeline[] }>(`/pacientes/${id}/timeline`)).eventos);
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) router.replace("/login");
        else toast.error(err instanceof ApiError ? err.message : "Erro");
      } finally {
        setLoading(false);
      }
    })();
  }, [id, router]);

  async function criarSessao(e: React.FormEvent) {
    e.preventDefault();
    try {
      const s = await api<Sessao>("/sessoes", {
        method: "POST",
        body: JSON.stringify({
          paciente_id: id,
          data: new Date(newSes.data).toISOString(),
          modalidade: newSes.modalidade,
          status: newSes.status,
          valor_centavos: reaisParaCentavos(newSes.valor),
        }),
      });
      setSessoes((r) => [s, ...r]);
      setNewSes({ data: "", modalidade: "presencial", status: "agendada", valor: "" });
      setAgendarOpen(false);
      toast.success("Sessão criada.");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Falha");
    }
  }

  async function novaEvolucao(sessaoId: string) {
    try {
      const ev = await api<{ id: string }>("/evolucoes", {
        method: "POST",
        body: JSON.stringify({ sessao_id: sessaoId }),
      });
      router.push(`/evolucoes/${ev.id}`);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Falha");
    }
  }

  async function exportar() {
    setConfirmExport(false);
    setExporting(true);
    try {
      // Download binário precisa do header Authorization (token em localStorage,
      // não em cookie) → fetch + blob, não <a href>.
      const res = await fetch(`${API_BASE}/pacientes/${id}/exportar`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      if (!res.ok) throw new Error(`Falha na exportação (${res.status})`);
      const blob = await res.blob();
      const cd = res.headers.get("Content-Disposition") || "";
      const m = cd.match(/filename=([^;]+)/);
      const fname = (m ? m[1].trim() : `export_${id}.zip`).replace(/"/g, "");
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = fname;
      document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(url);
      toast.success("Pacote exportado. Guarde-o com segurança.");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Falha ao exportar");
    } finally {
      setExporting(false);
    }
  }

  async function excluir() {
    setDeleting(true);
    try {
      await api(`/pacientes/${id}`, { method: "DELETE" });
      try { localStorage.removeItem("praxis.last_paciente"); } catch { /* ignora */ }
      toast.success("Paciente excluído.");
      router.push("/pacientes");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Falha ao excluir");
      setDeleting(false);
      setConfirmDel(false);
    }
  }

  function mudarTab(k: TabKey) {
    setTab(k);
    try {
      const url = new URL(window.location.href);
      url.searchParams.set("tab", k);
      url.searchParams.delete("novo");
      window.history.replaceState(null, "", url);
    } catch { /* ignora */ }
    document.getElementById(`tab-${k}`)?.focus();
  }

  if (loading) return (
    <>
      <Topbar />
      <main className="container-praxis" style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <Skeleton height={96} radius="var(--radius-lg)" />
        <Skeleton height={40} width="60%" />
        <Skeleton height={140} radius="var(--radius-lg)" />
      </main>
    </>
  );
  if (!pac) return null;

  // --- CTA primário contextual: "sessão hoje sem evolução" → Registrar evolução ---
  const hoje = new Date();
  const mesmoDia = (iso: string) => {
    const d = new Date(iso);
    return d.getFullYear() === hoje.getFullYear() && d.getMonth() === hoje.getMonth() && d.getDate() === hoje.getDate();
  };
  const sessoesComEvolucao = new Set(
    timeline.filter((e) => e.tipo_evento === "evolucao")
      .map((e) => (e.meta as { sessao_id?: string }).sessao_id)
      .filter((x): x is string => !!x),
  );
  const sessaoHojeSemEvolucao = sessoes.find(
    (s) => mesmoDia(s.data) && s.status !== "cancelada" && s.status !== "falta" && !sessoesComEvolucao.has(s.id),
  );

  return (
    <>
      <Topbar />
      <main className="container-praxis">
        <p style={{ margin: "0 0 12px" }}><Link className="link" href="/pacientes">← Pacientes</Link></p>
        <PacienteCard paciente={pac} sessoes={sessoes} />

        {/* Header de ação: 1 CTA primário contextual + menu "···" (secundárias e destrutivas separadas) */}
        <div style={{ marginTop: 12, display: "flex", gap: 8, alignItems: "center", justifyContent: "flex-end", flexWrap: "wrap" }}>
          {sessaoHojeSemEvolucao ? (
            <Button variant="primary" onClick={() => novaEvolucao(sessaoHojeSemEvolucao.id)}>
              <FilePlus size={16} /> Registrar evolução
            </Button>
          ) : (
            <Button variant="primary" onClick={() => setAgendarOpen(true)}>
              <CalendarPlus size={16} /> Agendar sessão
            </Button>
          )}
          <Button variant="ghost" onClick={() => setSofiaOpen(true)}>
            <PresenceMark size={16} /> Sofia
          </Button>
          <MenuAcoes
            secundarias={[
              { label: "Perguntar à Sofia", icon: <PresenceMark size={16} />, onClick: () => setSofiaOpen(true) },
              { label: "Novo instrumento", icon: <ClipboardList size={16} />, onClick: () => setInstrModal(true) },
              { label: "Preparar sessão", icon: <ClipboardCheck size={16} />, onClick: () => setPrepModal(true) },
              { label: "Gerar documento", icon: <FileSignature size={16} />, onClick: () => setDocModal(true) },
            ]}
            destrutivas={[
              { label: exporting ? "Exportando…" : "Exportar dados (LGPD)", icon: <Package size={16} />, onClick: () => setConfirmExport(true), disabled: exporting },
              { label: "Excluir paciente", icon: <Trash2 size={16} />, onClick: () => setConfirmDel(true) },
            ]}
          />
        </div>

        {/* Sub-navegação sticky (tablist navegável por teclado: ← → alternam seções) */}
        <div
          className="subnav"
          role="tablist"
          aria-label="Seções do paciente"
          onKeyDown={(e) => {
            if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
            e.preventDefault();
            const i = TABS.findIndex(([k]) => k === tab);
            const n = e.key === "ArrowRight" ? (i + 1) % TABS.length : (i - 1 + TABS.length) % TABS.length;
            mudarTab(TABS[n][0]);
          }}
        >
          {TABS.map(([k, label]) => (
            <button
              key={k}
              id={`tab-${k}`}
              role="tab"
              aria-selected={tab === k}
              aria-controls={`panel-${k}`}
              tabIndex={tab === k ? 0 : -1}
              className="subnav-tab"
              onClick={() => mudarTab(k)}
            >
              {label}
            </button>
          ))}
        </div>

        {/* ===== Visão geral ===== */}
        <div role="tabpanel" id="panel-visao" aria-labelledby="tab-visao" hidden={tab !== "visao"}>
          {resumo && resumo.sessoes.total > 0 ? (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 8 }}>
              <Card>
                <div style={{ color: "var(--muted)", fontSize: 12 }}>Sessões realizadas</div>
                <div style={{ fontFamily: "var(--font-mono)", fontSize: 20 }}>
                  {resumo.sessoes.realizadas}<span style={{ fontSize: 12, color: "var(--muted)" }}>/{resumo.sessoes.total}</span>
                </div>
                <div style={{ color: "var(--muted)", fontSize: 11 }}>
                  {resumo.sessoes.faltas} falta(s) · {resumo.sessoes.canceladas} cancel. · {resumo.sessoes.agendadas_futuras} agendada(s)
                </div>
              </Card>
              <Card>
                <div style={{ color: "var(--muted)", fontSize: 12 }}>Adesão</div>
                <div style={{ fontFamily: "var(--font-mono)", fontSize: 20 }}>
                  {resumo.adesao.den > 0 ? `${resumo.adesao.num}/${resumo.adesao.den}` : "—"}
                </div>
                <div style={{ color: "var(--muted)", fontSize: 11 }}>{resumo.adesao.criterio}</div>
              </Card>
              <Card>
                <div style={{ color: "var(--muted)", fontSize: 12 }}>Evoluções</div>
                <div style={{ fontFamily: "var(--font-mono)", fontSize: 20 }}>{resumo.evolucoes.assinadas}</div>
                <div style={{ color: "var(--muted)", fontSize: 11 }}>assinadas · {resumo.evolucoes.rascunho} rascunho</div>
              </Card>
              <Card>
                <div style={{ color: "var(--muted)", fontSize: 12 }}>Período de acompanhamento</div>
                <div style={{ fontFamily: "var(--font-mono)", fontSize: 13, marginTop: 4 }}>
                  {resumo.primeira_sessao ? new Date(resumo.primeira_sessao).toLocaleDateString("pt-BR") : "—"}
                  {" → "}
                  {resumo.ultima_sessao ? new Date(resumo.ultima_sessao).toLocaleDateString("pt-BR") : "—"}
                </div>
                <div style={{ color: "var(--muted)", fontSize: 11 }}>{resumo.instrumentos_aplicados} instrumento(s) aplicado(s)</div>
              </Card>
            </div>
          ) : (
            <p style={{ color: "var(--muted)" }}>Sem números ainda — agende e registre sessões para ver o resumo factual.</p>
          )}
          {pac && <ConformidadeIaCard pacienteId={pac.id} pacienteNome={pac.nome} />}
        </div>

        {/* ===== Trajetória ===== */}
        <div role="tabpanel" id="panel-trajetoria" aria-labelledby="tab-trajetoria" hidden={tab !== "trajetoria"}>
          {series.length === 0 && timeline.length === 0 && (
            <Card style={{ textAlign: "center", padding: 28 }}>
              <p style={{ color: "var(--muted)", margin: "0 0 12px" }}>
                Sem dados de trajetória ainda — escores e eventos aparecem aqui conforme o acompanhamento avança.
              </p>
              <Button variant="primary" onClick={() => setInstrModal(true)}>
                <ClipboardList size={16} /> Aplicar instrumento
              </Button>
            </Card>
          )}
          {series.length > 0 && (
            <>
              <SectionTitle icon={<Activity size={13} style={{ display: "inline", verticalAlign: "middle" }} />} margin="0 0 8px">Trajetória de escores</SectionTitle>
              <p style={{ color: "var(--muted)", fontSize: 12, margin: "0 0 12px" }}>
                Escores registrados das escalas reaplicadas. Bandas = faixas de severidade. A leitura clínica é do profissional.
              </p>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: 12 }}>
                {series.map((s) => (
                  <Card key={s.tipo}>
                    <GraficoTrajetoria serie={s} />
                  </Card>
                ))}
              </div>
            </>
          )}
          {timeline.length > 0 && (
            <>
              <SectionTitle icon={<CalendarClock size={13} style={{ display: "inline", verticalAlign: "middle" }} />} margin="24px 0 8px">Linha do tempo</SectionTitle>
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {timeline.map((ev) => (
                  <EventoLinha key={`${ev.tipo_evento}-${ev.ref_id}`} ev={ev} />
                ))}
              </div>
            </>
          )}
        </div>

        {/* ===== Sessões ===== */}
        <div role="tabpanel" id="panel-sessoes" aria-labelledby="tab-sessoes" hidden={tab !== "sessoes"}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", margin: "0 0 12px", gap: 8 }}>
            <SectionTitle margin="0">Timeline de sessões</SectionTitle>
            <Button onClick={() => setAgendarOpen(true)}><CalendarPlus size={16} /> Agendar sessão</Button>
          </div>
          {sessoes.length === 0 ? (
            <p style={{ color: "var(--muted)" }}>Nenhuma sessão registrada ainda — use “Agendar sessão”.</p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {sessoes.map((s) => (
                <Card key={s.id} className="row-stack" style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <div>
                    <div style={{ fontWeight: 500 }}>{dataRelativa(s.data)}</div>
                    <div style={{ color: "var(--muted)", fontSize: 13 }}>
                      <span className="badge">{modalidadeLabel(s.modalidade)}</span>{" "}
                      <StatusBadge status={s.status} />
                      {s.valor_centavos != null && <> <span className="badge">{formatCentavos(s.valor_centavos)}</span></>}
                    </div>
                  </div>
                  <div style={{ display: "flex", gap: 8 }}>
                    {s.modalidade === "online" && s.status !== "cancelada" && (
                      <Button variant="primary" onClick={() => setTelessessao(s.id)}>
                        <Video size={16} /> Sala
                      </Button>
                    )}
                    <Button onClick={() => setScribeSessao(s.id)}>
                      <PresenceMark size={16} /> Gerar evolução
                    </Button>
                    <Button onClick={() => novaEvolucao(s.id)}>
                      <FileText size={16} /> Em branco
                    </Button>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>

        {/* ===== Instrumentos ===== */}
        <div role="tabpanel" id="panel-instrumentos" aria-labelledby="tab-instrumentos" hidden={tab !== "instrumentos"}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", margin: "0 0 12px", gap: 8 }}>
            <SectionTitle margin="0">Instrumentos</SectionTitle>
            <Button onClick={() => setInstrModal(true)}><ClipboardList size={16} /> Novo instrumento</Button>
          </div>
          {respostas.length === 0 ? (
            <p style={{ color: "var(--muted)" }}>Nenhum instrumento aplicado ainda.</p>
          ) : respostas.map((r) => (
            <Card key={r.id} className="row-stack" style={{ marginBottom: 8, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div>
                <div style={{ fontWeight: 500 }}>{instrumentoTipoLabel(r.instrumento_tipo)} · {r.instrumento_versao}</div>
                <div style={{ color: "var(--muted)", fontSize: 12 }}>
                  <StatusBadge status={r.status} />{" "}
                  iniciado {dataRelativa(r.criado_em)}
                  {r.finalizado_em && ` · finalizado ${dataRelativa(r.finalizado_em)}`}
                </div>
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                <Link href={`/instrumentos/${r.id}`} className="btn">
                  {r.status === "finalizado" ? "Ver" : "Continuar"}
                </Link>
                {r.anexo_id && (
                  <a className="btn" href={`${API_BASE}/anexos/${r.anexo_id}/arquivo`} target="_blank" rel="noreferrer">
                    <Download size={14} /> PDF
                  </a>
                )}
              </div>
            </Card>
          ))}
        </div>

        {/* ===== Documentos (+ anexos do prontuário) ===== */}
        <div role="tabpanel" id="panel-documentos" aria-labelledby="tab-documentos" hidden={tab !== "documentos"}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", margin: "0 0 12px", gap: 8 }}>
            <SectionTitle margin="0">Documentos CFP</SectionTitle>
            <Button onClick={() => setDocModal(true)}><FileSignature size={16} /> Gerar documento</Button>
          </div>
          {documentos.length === 0 ? (
            <p style={{ color: "var(--muted)" }}>Nenhum documento gerado ainda.</p>
          ) : (
            documentos.map((d) => (
              <Card key={d.id} className="row-stack" style={{ marginBottom: 8, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <div>
                  <div style={{ fontWeight: 500 }}>{docTipoLabel(d.tipo)}</div>
                  <div style={{ color: "var(--muted)", fontSize: 12 }}>
                    <StatusBadge status={d.status} />{" "}
                    {d.finalidade.slice(0, 70)}{d.finalidade.length > 70 && "…"} · {dataRelativa(d.criado_em)}
                  </div>
                </div>
                <div style={{ display: "flex", gap: 8 }}>
                  <Link href={`/documentos/${d.id}`} className="btn">
                    {d.status === "assinado" ? "Ver" : "Editar"}
                  </Link>
                  {d.anexo_pdf_id && (
                    <a className="btn" href={`${API_BASE}/anexos/${d.anexo_pdf_id}/arquivo`} target="_blank" rel="noreferrer">
                      <Download size={14} /> PDF
                    </a>
                  )}
                </div>
              </Card>
            ))
          )}
          {anexos.length > 0 && (
            <>
              <SectionTitle icon={<Paperclip size={13} style={{ display: "inline", verticalAlign: "middle" }} />} margin="24px 0 8px">Anexos do prontuário</SectionTitle>
              <Card style={{ padding: 0 }}>
                <table className="table-cards" style={{ width: "100%", borderCollapse: "collapse" }}>
                  <thead>
                    <tr style={{ textAlign: "left", color: "var(--muted)", fontSize: 12 }}>
                      <th style={{ padding: 12 }}>Título</th>
                      <th style={{ padding: 12 }}>Tamanho</th>
                      <th style={{ padding: 12 }}>Criado em</th>
                      <th style={{ padding: 12 }}></th>
                    </tr>
                  </thead>
                  <tbody>
                    {anexos.map((a) => (
                      <tr key={a.id} style={{ borderTop: "1px solid var(--border)", background: novoAnexoId === a.id ? "var(--amber-100)" : undefined }}>
                        <td data-label="Título" style={{ padding: 12 }}>{a.titulo}</td>
                        <td data-label="Tamanho" style={{ padding: 12, color: "var(--muted)" }}>{(a.bytes / 1024).toFixed(0)} KB</td>
                        <td data-label="Criado em" style={{ padding: 12, color: "var(--muted)" }}>{dataRelativa(a.criado_em)}</td>
                        <td data-label="" style={{ padding: 12, textAlign: "right" }}>
                          <a className="link" href={`${API_BASE}/anexos/${a.id}/arquivo`} target="_blank" rel="noreferrer">
                            <Download size={13} style={{ display: "inline", verticalAlign: "middle" }} /> baixar
                          </a>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Card>
            </>
          )}
        </div>
      </main>
      <Drawer open={agendarOpen} title="Agendar sessão" onClose={() => setAgendarOpen(false)}>
        <form onSubmit={criarSessao} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <Field label="Data e hora">
            <input className="input" type="datetime-local" required
              value={newSes.data} onChange={(e) => setNewSes({ ...newSes, data: e.target.value })} />
          </Field>
          <Field label="Modalidade">
            <select className="input" value={newSes.modalidade} onChange={(e) => setNewSes({ ...newSes, modalidade: e.target.value })}>
              <option value="presencial">Presencial</option>
              <option value="online">Online</option>
            </select>
          </Field>
          <Field label="Status">
            <select className="input" value={newSes.status} onChange={(e) => setNewSes({ ...newSes, status: e.target.value })}>
              <option value="agendada">Agendada</option>
              <option value="realizada">Realizada</option>
              <option value="cancelada">Cancelada</option>
              <option value="falta">Falta</option>
            </select>
          </Field>
          <Field label="Valor (R$)">
            <input className="input" inputMode="decimal" placeholder="150,00"
              value={newSes.valor} onChange={(e) => setNewSes({ ...newSes, valor: e.target.value })} />
          </Field>
          <Button variant="primary" style={{ marginTop: 4 }}><CalendarPlus size={16} /> Agendar</Button>
        </form>
      </Drawer>
      {scribeSessao && (
        <ScribeModal sessaoId={scribeSessao} onClose={() => setScribeSessao(null)} />
      )}
      {telessessao && pac && (
        <TelessessaoModal sessaoId={telessessao} pacienteId={pac.id} pacienteNome={pac.nome} onClose={() => setTelessessao(null)} />
      )}
      {instrModal && (
        <InstrumentoModal pacienteId={id} onClose={() => setInstrModal(false)} />
      )}
      {(prepModal || prepContexto !== null) && (
        <PrepararSessaoModal
          pacienteId={id}
          sofiaContexto={prepContexto ?? undefined}
          onClose={() => { setPrepModal(false); setPrepContexto(null); }}
        />
      )}
      {docModal && (
        <DocumentoModal pacienteId={id} onClose={() => setDocModal(false)} />
      )}
      <SofiaPainelProntuario
        open={sofiaOpen}
        pacienteId={id}
        respostas={respostas}
        series={series}
        onClose={() => setSofiaOpen(false)}
        onUsarNaPreparacao={(contexto) => { setSofiaOpen(false); setPrepContexto(contexto); }}
      />
      <ConfirmDialog
        open={confirmExport}
        title="Exportar dados (LGPD)"
        description={`Será gerado um pacote (.zip) com o prontuário completo de ${formatNome(pac.nome)}: dados pessoais decifrados, evoluções, documentos, instrumentos e os anexos originais. O arquivo contém informação sensível — você é responsável por armazená-lo e transmiti-lo com segurança. Nada é apagado ou alterado.`}
        confirmLabel="Baixar pacote"
        busy={exporting}
        onConfirm={exportar}
        onCancel={() => setConfirmExport(false)}
      />
      <ConfirmDialog
        open={confirmDel}
        title="Excluir paciente"
        description={`O prontuário de ${formatNome(pac.nome)} será removido da lista (soft-delete, mantido sob guarda legal de 20 anos). Esta ação exige nova inclusão para reverter.`}
        confirmLabel="Excluir paciente"
        busy={deleting}
        onConfirm={excluir}
        onCancel={() => setConfirmDel(false)}
      />
    </>
  );
}

const EVENTO_ICON: Record<string, typeof CalendarClock> = {
  sessao: CalendarClock, evolucao: FileText, instrumento: ClipboardList, documento: FileSignature,
};

function EventoLinha({ ev }: { ev: EventoTimeline }) {
  const Icon = EVENTO_ICON[ev.tipo_evento] || CalendarClock;
  const href =
    ev.tipo_evento === "evolucao" ? `/evolucoes/${ev.ref_id}` :
    ev.tipo_evento === "instrumento" ? `/instrumentos/${ev.ref_id}` :
    ev.tipo_evento === "documento" ? `/documentos/${ev.ref_id}` : null;

  const m = ev.meta as {
    status?: string; assinada?: boolean; escore?: number; faixa?: string;
    subescores?: { rotulo: string; escore: number; faixa?: string }[];
  };
  const badges: React.ReactNode[] = [];
  if (m.assinada === true) badges.push(<StatusBadge key="a" status="assinada" />);
  else if (typeof m.status === "string") badges.push(<StatusBadge key="s" status={m.status} />);
  if (typeof m.escore === "number") badges.push(<span key="e" className="badge">escore {m.escore}{m.faixa ? ` · ${m.faixa}` : ""}</span>);
  if (Array.isArray(m.subescores)) m.subescores.forEach((s, i) =>
    badges.push(<span key={`ss${i}`} className="badge">{s.rotulo} {s.escore}</span>));

  const inner = (
    <Card style={{ display: "flex", alignItems: "center", gap: 10, padding: "10px 14px" }}>
      <Icon size={16} color="var(--brand-2)" style={{ flexShrink: 0 }} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontWeight: 500, fontSize: 14 }}>{ev.titulo}</div>
        <div style={{ color: "var(--muted)", fontSize: 12, display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
          <span style={{ fontFamily: "var(--font-mono)" }}>{dataRelativa(ev.data)}</span>
          {badges}
        </div>
      </div>
      {href && <span className="link" style={{ fontSize: 13, flexShrink: 0 }}>abrir →</span>}
    </Card>
  );
  return href ? <Link href={href} style={{ textDecoration: "none", color: "inherit" }}>{inner}</Link> : inner;
}
