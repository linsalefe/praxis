"use client";

import { useEffect, useState, use } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import { CalendarPlus, FileText, Sparkles } from "lucide-react";
import { api, ApiError, getToken } from "@/lib/api";
import { Topbar } from "@/components/Topbar";

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

  useEffect(() => {
    if (!getToken()) return void router.replace("/login");
    (async () => {
      try {
        setPac(await api<Paciente>(`/pacientes/${id}`));
        setSessoes(await api<Sessao[]>(`/sessoes/paciente/${id}`));
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

  if (loading) return (<><Topbar /><main className="container-praxis"><p style={{ color: "var(--muted)" }}>Carregando…</p></main></>);
  if (!pac) return null;

  return (
    <>
      <Topbar />
      <main className="container-praxis">
        <p style={{ margin: 0 }}><Link className="link" href="/pacientes">← Pacientes</Link></p>
        <h1 style={{ fontSize: 22, margin: "8px 0 4px" }}>{pac.nome}</h1>
        <p style={{ color: "var(--muted)", marginTop: 0 }}>
          {[pac.contato, pac.nascimento, pac.documento, pac.sexo].filter(Boolean).join(" · ") || "Sem dados adicionais."}
        </p>
        <Link href={`/sofia?paciente_id=${id}`} className="btn" style={{ marginTop: 8 }}>
          <Sparkles size={16} /> Perguntar à Sofia sobre este caso
        </Link>

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
          <p style={{ color: "var(--muted)" }}>Nenhuma sessão registrada.</p>
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
                <button className="btn" onClick={() => novaEvolucao(s.id)}>
                  <FileText size={16} /> Nova evolução
                </button>
              </div>
            ))}
          </div>
        )}
      </main>
    </>
  );
}
