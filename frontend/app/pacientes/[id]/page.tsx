"use client";

import { useEffect, useState, use } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import { CalendarPlus, ClipboardCheck, ClipboardList, Download, FileSignature, FileText, Paperclip, Trash2 } from "lucide-react";
import { api, ApiError, getToken } from "@/lib/api";
import { Topbar } from "@/components/Topbar";
import { ScribeModal } from "@/components/ScribeModal";
import { InstrumentoModal } from "@/components/InstrumentoModal";
import { PrepararSessaoModal } from "@/components/PrepararSessaoModal";
import { DocumentoModal } from "@/components/DocumentoModal";
import { PresenceMark } from "@/components/ui/PresenceMark";
import { PacienteCard } from "@/components/ui/PacienteCard";
import { Skeleton } from "@/components/ui/Skeleton";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";

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
};

export default function FichaPacientePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const [pac, setPac] = useState<Paciente | null>(null);
  const [sessoes, setSessoes] = useState<Sessao[]>([]);
  const [loading, setLoading] = useState(true);
  const [newSes, setNewSes] = useState({ data: "", modalidade: "presencial", status: "agendada" });
  const [scribeSessao, setScribeSessao] = useState<string | null>(null);
  const [instrModal, setInstrModal] = useState(false);
  const [prepModal, setPrepModal] = useState(false);
  const [docModal, setDocModal] = useState(false);
  const [respostas, setRespostas] = useState<RespInstr[]>([]);
  const [anexos, setAnexos] = useState<Anexo[]>([]);
  const [documentos, setDocumentos] = useState<DocumentoCFP[]>([]);
  const [confirmDel, setConfirmDel] = useState(false);
  const [deleting, setDeleting] = useState(false);

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
        }),
      });
      setSessoes((r) => [s, ...r]);
      setNewSes({ data: "", modalidade: "presencial", status: "agendada" });
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

  return (
    <>
      <Topbar />
      <main className="container-praxis">
        <p style={{ margin: "0 0 12px" }}><Link className="link" href="/pacientes">← Pacientes</Link></p>
        <PacienteCard paciente={pac} sessoes={sessoes} />
        <div style={{ marginTop: 12, display: "flex", gap: 8, flexWrap: "wrap" }}>
          <Link href={`/sofia?paciente_id=${id}`} className="btn">
            <PresenceMark size={16} /> Perguntar à Sofia
          </Link>
          <button className="btn" onClick={() => setInstrModal(true)}>
            <ClipboardList size={16} /> Novo instrumento
          </button>
          <button className="btn" onClick={() => setPrepModal(true)}>
            <ClipboardCheck size={16} /> Preparar sessão
          </button>
          <button className="btn" onClick={() => setDocModal(true)}>
            <FileSignature size={16} /> Gerar documento
          </button>
          <button className="btn btn-danger" onClick={() => setConfirmDel(true)} style={{ marginLeft: "auto" }}>
            <Trash2 size={16} /> Excluir paciente
          </button>
        </div>

        {documentos.length > 0 && (
          <>
            <h2 style={{ fontSize: 15, margin: "24px 0 8px", color: "var(--muted)" }}>Documentos CFP</h2>
            {documentos.map((d) => (
              <div key={d.id} className="card" style={{ marginBottom: 8, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <div>
                  <div style={{ fontWeight: 500, textTransform: "capitalize" }}>{d.tipo}</div>
                  <div style={{ color: "var(--muted)", fontSize: 12 }}>
                    <span className="badge">{d.status}</span>{" "}
                    {d.finalidade.slice(0, 70)}{d.finalidade.length > 70 && "…"} · {new Date(d.criado_em).toLocaleDateString("pt-BR")}
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
              </div>
            ))}
          </>
        )}

        {(respostas.length > 0 || anexos.length > 0) && (
          <>
            <h2 style={{ fontSize: 15, margin: "24px 0 8px", color: "var(--muted)" }}>Instrumentos</h2>
            {respostas.length === 0 && <p style={{ color: "var(--muted)" }}>Nenhum instrumento aplicado ainda.</p>}
            {respostas.map((r) => (
              <div key={r.id} className="card" style={{ marginBottom: 8, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <div>
                  <div style={{ fontWeight: 500 }}>{r.instrumento_tipo.toUpperCase()} · {r.instrumento_versao}</div>
                  <div style={{ color: "var(--muted)", fontSize: 12 }}>
                    <span className="badge">{r.status}</span>{" "}
                    iniciado {new Date(r.criado_em).toLocaleDateString("pt-BR")}
                    {r.finalizado_em && ` · finalizado ${new Date(r.finalizado_em).toLocaleDateString("pt-BR")}`}
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
              </div>
            ))}

            {anexos.length > 0 && (
              <>
                <h2 style={{ fontSize: 15, margin: "24px 0 8px", color: "var(--muted)" }}>
                  <Paperclip size={13} style={{ display: "inline", verticalAlign: "middle" }} /> Anexos do prontuário
                </h2>
                <div className="card" style={{ padding: 0 }}>
                  <table style={{ width: "100%", borderCollapse: "collapse" }}>
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
                        <tr key={a.id} style={{ borderTop: "1px solid var(--border)" }}>
                          <td style={{ padding: 12 }}>{a.titulo}</td>
                          <td style={{ padding: 12, color: "var(--muted)" }}>{(a.bytes / 1024).toFixed(0)} KB</td>
                          <td style={{ padding: 12, color: "var(--muted)" }}>{new Date(a.criado_em).toLocaleString("pt-BR")}</td>
                          <td style={{ padding: 12, textAlign: "right" }}>
                            <a className="link" href={`${API_BASE}/anexos/${a.id}/arquivo`} target="_blank" rel="noreferrer">
                              <Download size={13} style={{ display: "inline", verticalAlign: "middle" }} /> baixar
                            </a>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}
          </>
        )}

        <div className="card" style={{ marginTop: 20 }}>
          <h2 style={{ fontSize: 15, margin: "0 0 12px", color: "var(--muted)" }}>Agendar sessão</h2>
          <form onSubmit={criarSessao} style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr auto", gap: 8, alignItems: "end" }}>
            <div>
              <label className="label">Data e hora</label>
              <input className="input" type="datetime-local" required
                value={newSes.data} onChange={(e) => setNewSes({ ...newSes, data: e.target.value })} />
            </div>
            <div>
              <label className="label">Modalidade</label>
              <select className="input" value={newSes.modalidade} onChange={(e) => setNewSes({ ...newSes, modalidade: e.target.value })}>
                <option value="presencial">Presencial</option>
                <option value="online">Online</option>
              </select>
            </div>
            <div>
              <label className="label">Status</label>
              <select className="input" value={newSes.status} onChange={(e) => setNewSes({ ...newSes, status: e.target.value })}>
                <option value="agendada">Agendada</option>
                <option value="realizada">Realizada</option>
                <option value="cancelada">Cancelada</option>
                <option value="falta">Falta</option>
              </select>
            </div>
            <button className="btn btn-primary"><CalendarPlus size={16} /> Agendar</button>
          </form>
        </div>

        <h2 style={{ fontSize: 15, margin: "24px 0 12px", color: "var(--muted)" }}>Timeline de sessões</h2>
        {sessoes.length === 0 ? (
          <p style={{ color: "var(--muted)" }}>Nenhuma sessão registrada ainda — agende a primeira acima.</p>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {sessoes.map((s) => (
              <div key={s.id} className="card" style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <div>
                  <div style={{ fontWeight: 500 }}>{new Date(s.data).toLocaleString("pt-BR")}</div>
                  <div style={{ color: "var(--muted)", fontSize: 13 }}>
                    <span className="badge">{s.modalidade}</span>{" "}
                    <span className="badge">{s.status}</span>
                  </div>
                </div>
                <div style={{ display: "flex", gap: 8 }}>
                  <button className="btn" onClick={() => setScribeSessao(s.id)}>
                    <PresenceMark size={16} /> Gerar evolução
                  </button>
                  <button className="btn" onClick={() => novaEvolucao(s.id)}>
                    <FileText size={16} /> Em branco
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
      {scribeSessao && (
        <ScribeModal sessaoId={scribeSessao} onClose={() => setScribeSessao(null)} />
      )}
      {instrModal && (
        <InstrumentoModal pacienteId={id} onClose={() => setInstrModal(false)} />
      )}
      {prepModal && (
        <PrepararSessaoModal pacienteId={id} onClose={() => setPrepModal(false)} />
      )}
      {docModal && (
        <DocumentoModal pacienteId={id} onClose={() => setDocModal(false)} />
      )}
      <ConfirmDialog
        open={confirmDel}
        title="Excluir paciente"
        description={`O prontuário de ${pac.nome} será removido da lista (soft-delete, mantido sob guarda legal de 20 anos). Esta ação exige nova inclusão para reverter.`}
        confirmLabel="Excluir paciente"
        busy={deleting}
        onConfirm={excluir}
        onCancel={() => setConfirmDel(false)}
      />
    </>
  );
}
