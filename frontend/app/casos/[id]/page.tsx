"use client";

import { useEffect, useState, use } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import { CheckCircle2, FileText, RotateCcw, Save } from "lucide-react";
import { api, ApiError, getToken } from "@/lib/api";
import { formatNome } from "@/lib/format";
import { dataRelativa, dataCurtaComHora } from "@/lib/date";
import { Topbar } from "@/components/Topbar";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { SectionTitle } from "@/components/ui/SectionTitle";
import { Skeleton } from "@/components/ui/Skeleton";
import { EmptyState } from "@/components/ui/EmptyState";

type Secao = { id: string; titulo: string; ajuda: string };
type PtsVersao = {
  id: string; caso_id: string; versao: number;
  conteudo: Record<string, string>; criado_por: string; criado_em: string;
};
type Caso = {
  id: string; paciente_id: string; titulo: string | null; status: string;
  aberto_em: string; encerrado_em: string | null; criado_em: string;
  pts_atual: PtsVersao | null;
};
type Paciente = { id: string; nome: string };

export default function CasoPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const [caso, setCaso] = useState<Caso | null>(null);
  const [pac, setPac] = useState<Paciente | null>(null);
  const [secoes, setSecoes] = useState<Secao[]>([]);
  const [historico, setHistorico] = useState<PtsVersao[]>([]);
  const [conteudo, setConteudo] = useState<Record<string, string>>({});
  const [titulo, setTitulo] = useState("");
  const [loading, setLoading] = useState(true);
  const [salvando, setSalvando] = useState(false);

  async function carregar() {
    const [c, def, hist] = await Promise.all([
      api<Caso>(`/casos/${id}`),
      api<{ secoes: Secao[] }>(`/casos/pts/definicao`),
      api<PtsVersao[]>(`/casos/${id}/pts`),
    ]);
    setCaso(c);
    setSecoes(def.secoes);
    setHistorico(hist);
    setTitulo(c.titulo || "");
    setConteudo(c.pts_atual?.conteudo || {});
    try {
      const p = await api<Paciente>(`/pacientes/${c.paciente_id}`);
      setPac(p);
    } catch { /* nome é acessório */ }
  }

  useEffect(() => {
    if (!getToken()) return void router.replace("/login");
    (async () => {
      try {
        await carregar();
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) router.replace("/login");
        else toast.error(err instanceof ApiError ? err.message : "Falha ao carregar o caso");
      } finally {
        setLoading(false);
      }
    })();
  }, [id, router]);

  async function salvarPts() {
    setSalvando(true);
    try {
      await api(`/casos/${id}/pts`, { method: "POST", body: JSON.stringify({ conteudo }) });
      toast.success("Nova versão do PTS salva.");
      await carregar();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Falha ao salvar");
    } finally {
      setSalvando(false);
    }
  }

  async function salvarTitulo() {
    try {
      await api(`/casos/${id}`, { method: "PATCH", body: JSON.stringify({ titulo: titulo.trim() || null }) });
      toast.success("Título atualizado.");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Falha");
    }
  }

  async function alternarStatus() {
    if (!caso) return;
    const novo = caso.status === "ativo" ? "encerrado" : "ativo";
    try {
      const atualizado = await api<Caso>(`/casos/${id}`, { method: "PATCH", body: JSON.stringify({ status: novo }) });
      setCaso(atualizado);
      toast.success(novo === "encerrado" ? "Caso encerrado." : "Caso reaberto.");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Falha");
    }
  }

  if (loading) {
    return (
      <>
        <Topbar />
        <main className="container-praxis"><Skeleton /></main>
      </>
    );
  }
  if (!caso) return null;

  return (
    <>
      <Topbar />
      <main className="container-praxis">
        <p style={{ margin: "0 0 12px" }}>
          <Link className="link" href={`/pacientes/${caso.paciente_id}?tab=casos`}>← Voltar ao paciente</Link>
        </p>

        <Card style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12, flexWrap: "wrap" }}>
          <div style={{ flex: 1, minWidth: 240 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
              <StatusBadge status={caso.status} />
              {pac && (
                <Link className="link" href={`/pacientes/${caso.paciente_id}`}>{formatNome(pac.nome)}</Link>
              )}
              <span style={{ color: "var(--muted)", fontSize: 12 }}>· aberto {dataRelativa(caso.aberto_em)}</span>
            </div>
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <input
                className="input"
                placeholder="Título do caso (ex.: linha de cuidado, foco)"
                value={titulo}
                onChange={(e) => setTitulo(e.target.value)}
                onBlur={salvarTitulo}
                style={{ maxWidth: 420 }}
              />
            </div>
          </div>
          <Button onClick={alternarStatus}>
            {caso.status === "ativo" ? <><CheckCircle2 size={16} /> Encerrar caso</> : <><RotateCcw size={16} /> Reabrir</>}
          </Button>
        </Card>

        {/* Editor do PTS */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", margin: "20px 0 8px", gap: 8 }}>
          <SectionTitle margin="0">
            Projeto Terapêutico Singular
            {caso.pts_atual && (
              <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--muted)" }}> · v{caso.pts_atual.versao}</span>
            )}
          </SectionTitle>
          <Button variant="primary" onClick={salvarPts} loading={salvando}>
            <Save size={16} /> Salvar nova versão
          </Button>
        </div>
        <p style={{ color: "var(--muted)", fontSize: 12, margin: "0 0 12px" }}>
          Cada save cria uma nova versão (o histórico é preservado). v1 individual —
          a co-autoria pela equipe entra numa próxima onda.
        </p>

        {secoes.map((s) => (
          <div key={s.id} style={{ marginBottom: 14 }}>
            <label htmlFor={`pts-${s.id}`} style={{ fontSize: 14, fontWeight: 600 }}>{s.titulo}</label>
            <div style={{ fontSize: 11, color: "var(--muted)", margin: "2px 0 4px" }}>{s.ajuda}</div>
            <textarea
              id={`pts-${s.id}`}
              className="input"
              rows={3}
              value={conteudo[s.id] || ""}
              onChange={(e) => setConteudo((v) => ({ ...v, [s.id]: e.target.value }))}
            />
          </div>
        ))}

        {/* Histórico de versões */}
        <SectionTitle margin="24px 0 8px">Histórico do PTS</SectionTitle>
        {historico.length === 0 ? (
          <EmptyState icone={<FileText size={28} />} frase="Nenhuma versão salva ainda." />
        ) : (
          historico.map((v) => (
            <Card key={v.id} style={{ marginBottom: 8 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span className="badge">v{v.versao}</span>
                <span style={{ color: "var(--muted)", fontSize: 12 }}>{dataCurtaComHora(v.criado_em)}</span>
              </div>
              <div style={{ marginTop: 6, display: "flex", flexDirection: "column", gap: 6 }}>
                {secoes.filter((s) => v.conteudo[s.id]).map((s) => (
                  <div key={s.id}>
                    <div style={{ fontSize: 12, fontWeight: 600 }}>{s.titulo}</div>
                    <div style={{ fontSize: 13, whiteSpace: "pre-wrap" }}>{v.conteudo[s.id]}</div>
                  </div>
                ))}
              </div>
            </Card>
          ))
        )}
      </main>
    </>
  );
}
