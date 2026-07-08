"use client";

import { useEffect, useState, use } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import { UserPlus, Save, Trash2, X } from "lucide-react";
import { api, ApiError, getToken } from "@/lib/api";
import { grupoTipoLabel } from "@/lib/labels";
import { formatNome } from "@/lib/format";
import { dataCurtaComHora } from "@/lib/date";
import { Topbar } from "@/components/Topbar";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Field } from "@/components/ui/Field";
import { Skeleton } from "@/components/ui/Skeleton";
import { SectionTitle } from "@/components/ui/SectionTitle";

type Participante = {
  id: string; paciente_id: string | null; nome: string; e_paciente: boolean; presente: boolean;
};
type Encontro = {
  id: string; tipo: string; titulo: string; data: string;
  local: string | null; tema: string | null; registro: string | null;
  criado_em: string; participantes: Participante[];
};
type Paciente = { id: string; nome: string };

export default function EncontroPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const [enc, setEnc] = useState<Encontro | null>(null);
  const [pacientes, setPacientes] = useState<Paciente[]>([]);
  const [loading, setLoading] = useState(true);
  const [registro, setRegistro] = useState("");
  const [salvando, setSalvando] = useState(false);
  const [pacienteSel, setPacienteSel] = useState("");
  const [nomeLivre, setNomeLivre] = useState("");

  async function carregar() {
    const e = await api<Encontro>(`/grupos/${id}`);
    setEnc(e);
    setRegistro(e.registro || "");
  }

  useEffect(() => {
    if (!getToken()) return void router.replace("/login");
    (async () => {
      try {
        await carregar();
        try { setPacientes(await api<Paciente[]>("/pacientes")); } catch { /* opcional */ }
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) router.replace("/login");
        else toast.error(err instanceof ApiError ? err.message : "Falha ao carregar");
      } finally {
        setLoading(false);
      }
    })();
  }, [id, router]);

  async function salvarRegistro() {
    setSalvando(true);
    try {
      await api(`/grupos/${id}`, { method: "PATCH", body: JSON.stringify({ registro: registro.trim() || null }) });
      toast.success("Registro salvo.");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Falha");
    } finally {
      setSalvando(false);
    }
  }

  async function adicionar(payload: { paciente_id?: string; nome_livre?: string }) {
    try {
      const e = await api<Encontro>(`/grupos/${id}/participantes`, {
        method: "POST", body: JSON.stringify({ ...payload, presente: true }),
      });
      setEnc(e);
      setPacienteSel("");
      setNomeLivre("");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Falha ao adicionar");
    }
  }

  async function remover(participanteId: string) {
    try {
      await api(`/grupos/${id}/participantes/${participanteId}`, { method: "DELETE" });
      setEnc((e) => e ? { ...e, participantes: e.participantes.filter((p) => p.id !== participanteId) } : e);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Falha ao remover");
    }
  }

  if (loading) {
    return (<><Topbar /><main className="container-praxis"><Skeleton /></main></>);
  }
  if (!enc) return null;

  // Pacientes ainda não adicionados (evita duplicar no seletor).
  const jaAdicionados = new Set(enc.participantes.map((p) => p.paciente_id).filter(Boolean));
  const disponiveis = pacientes.filter((p) => !jaAdicionados.has(p.id));

  return (
    <>
      <Topbar />
      <main className="container-praxis">
        <p style={{ margin: "0 0 12px" }}><Link className="link" href="/grupos">← Grupos</Link></p>

        <Card>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span className="badge badge-info">{grupoTipoLabel(enc.tipo)}</span>
            <h2 style={{ margin: 0, fontSize: 18 }}>{enc.titulo}</h2>
          </div>
          <div style={{ color: "var(--muted)", fontSize: 13, marginTop: 4 }}>
            {dataCurtaComHora(enc.data)}{enc.local && ` · ${enc.local}`}{enc.tema && ` · ${enc.tema}`}
          </div>
        </Card>

        <SectionTitle margin="20px 0 8px">Participantes ({enc.participantes.length})</SectionTitle>
        {enc.participantes.length === 0 ? (
          <p style={{ color: "var(--muted)", fontSize: 13 }}>Nenhum participante ainda.</p>
        ) : (
          enc.participantes.map((p) => (
            <Card key={p.id} style={{ marginBottom: 6, display: "flex", alignItems: "center", justifyContent: "space-between", padding: "10px 14px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ fontWeight: 500 }}>
                  {p.e_paciente && p.paciente_id ? (
                    <Link className="link" href={`/pacientes/${p.paciente_id}`}>{formatNome(p.nome)}</Link>
                  ) : formatNome(p.nome)}
                </span>
                {!p.e_paciente && <span className="badge badge-neutral">comunidade</span>}
                {!p.presente && <span className="badge badge-risk">ausente</span>}
              </div>
              <Button onClick={() => remover(p.id)} aria-label="Remover participante"><Trash2 size={14} /></Button>
            </Card>
          ))
        )}

        {/* Adicionar participante */}
        <Card style={{ marginTop: 12, display: "flex", flexDirection: "column", gap: 12 }}>
          <div style={{ fontWeight: 600, fontSize: 14 }}>Adicionar participante</div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "flex-end" }}>
            <Field label="Paciente do serviço">
              <select className="input" value={pacienteSel} onChange={(e) => setPacienteSel(e.target.value)} style={{ minWidth: 200 }}>
                <option value="">Selecionar…</option>
                {disponiveis.map((p) => (<option key={p.id} value={p.id}>{formatNome(p.nome)}</option>))}
              </select>
            </Field>
            <Button disabled={!pacienteSel} onClick={() => adicionar({ paciente_id: pacienteSel })}>
              <UserPlus size={14} /> Adicionar paciente
            </Button>
          </div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "flex-end" }}>
            <Field label="Ou pessoa da comunidade (nome livre)">
              <input className="input" value={nomeLivre} onChange={(e) => setNomeLivre(e.target.value)} style={{ minWidth: 200 }} />
            </Field>
            <Button disabled={!nomeLivre.trim()} onClick={() => adicionar({ nome_livre: nomeLivre.trim() })}>
              <UserPlus size={14} /> Adicionar
            </Button>
          </div>
        </Card>

        {/* Registro do encontro */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", margin: "20px 0 8px", gap: 8 }}>
          <SectionTitle margin="0">Registro do encontro</SectionTitle>
          <Button variant="primary" onClick={salvarRegistro} loading={salvando}><Save size={16} /> Salvar</Button>
        </div>
        <textarea
          className="input"
          rows={6}
          placeholder="O que aconteceu no encontro, temas trabalhados, encaminhamentos coletivos…"
          value={registro}
          onChange={(e) => setRegistro(e.target.value)}
        />
      </main>
    </>
  );
}
