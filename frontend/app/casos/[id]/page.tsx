"use client";

import { useEffect, useState, use } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import { CheckCircle2, FileText, RotateCcw, Save, Trash2, UserPlus } from "lucide-react";
import { api, ApiError, getToken } from "@/lib/api";
import { formatNome } from "@/lib/format";
import { dataRelativa, dataCurtaComHora } from "@/lib/date";
import { Topbar } from "@/components/Topbar";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Field } from "@/components/ui/Field";
import { SectionTitle } from "@/components/ui/SectionTitle";
import { Skeleton } from "@/components/ui/Skeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import { vinculoTipoLabel } from "@/lib/labels";

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
type MembroRede = {
  id: string; caso_id: string; nome: string; papel: string | null;
  tipo_vinculo: string; forca_vinculo: string; observacoes: string | null;
};

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
  const [rede, setRede] = useState<MembroRede[]>([]);
  const [novoMembro, setNovoMembro] = useState({ nome: "", papel: "", tipo_vinculo: "familiar", forca_vinculo: "forte" });
  const [addingMembro, setAddingMembro] = useState(false);

  async function carregar() {
    const [c, def, hist, membros] = await Promise.all([
      api<Caso>(`/casos/${id}`),
      api<{ secoes: Secao[] }>(`/casos/pts/definicao`),
      api<PtsVersao[]>(`/casos/${id}/pts`),
      api<MembroRede[]>(`/casos/${id}/rede`),
    ]);
    setCaso(c);
    setSecoes(def.secoes);
    setHistorico(hist);
    setRede(membros);
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

  async function adicionarMembro() {
    if (!novoMembro.nome.trim()) return;
    setAddingMembro(true);
    try {
      const m = await api<MembroRede>(`/casos/${id}/rede`, {
        method: "POST",
        body: JSON.stringify({
          nome: novoMembro.nome.trim(), papel: novoMembro.papel.trim() || null,
          tipo_vinculo: novoMembro.tipo_vinculo, forca_vinculo: novoMembro.forca_vinculo,
        }),
      });
      setRede((r) => [...r, m]);
      setNovoMembro({ nome: "", papel: "", tipo_vinculo: "familiar", forca_vinculo: "forte" });
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Falha ao adicionar");
    } finally {
      setAddingMembro(false);
    }
  }

  async function mudarForca(membroId: string, forca: string) {
    try {
      const m = await api<MembroRede>(`/casos/${id}/rede/${membroId}`, {
        method: "PATCH", body: JSON.stringify({ forca_vinculo: forca }),
      });
      setRede((r) => r.map((x) => x.id === membroId ? m : x));
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Falha");
    }
  }

  async function removerMembro(membroId: string) {
    try {
      await api(`/casos/${id}/rede/${membroId}`, { method: "DELETE" });
      setRede((r) => r.filter((x) => x.id !== membroId));
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Falha ao remover");
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

        {/* Rede de apoio (genograma/ecomapa) */}
        <SectionTitle margin="24px 0 8px">Rede de apoio</SectionTitle>
        <p style={{ color: "var(--muted)", fontSize: 12, margin: "0 0 12px" }}>
          Pessoas da família e de serviços/comunidade ligadas ao cuidado, com tipo e força do vínculo.
        </p>
        {rede.length === 0 ? (
          <EmptyState icone={<UserPlus size={28} />} frase="Nenhum membro na rede ainda." />
        ) : (
          rede.map((m) => (
            <Card key={m.id} style={{ marginBottom: 6, display: "flex", alignItems: "center", justifyContent: "space-between", padding: "10px 14px", gap: 8, flexWrap: "wrap" }}>
              <div>
                <div style={{ fontWeight: 500 }}>
                  {m.nome}
                  {m.papel && <span style={{ color: "var(--muted)", fontWeight: 400 }}> · {m.papel}</span>}
                </div>
                <div style={{ display: "flex", gap: 6, alignItems: "center", marginTop: 4 }}>
                  <span className="badge badge-neutral">{vinculoTipoLabel(m.tipo_vinculo)}</span>
                  <StatusBadge status={`vinculo_${m.forca_vinculo}`} />
                </div>
              </div>
              <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                <select
                  className="input"
                  aria-label="Força do vínculo"
                  value={m.forca_vinculo}
                  onChange={(e) => mudarForca(m.id, e.target.value)}
                  style={{ width: "auto", padding: "6px 8px" }}
                >
                  <option value="forte">Vínculo forte</option>
                  <option value="fragil">Vínculo frágil</option>
                  <option value="conflito">Conflito</option>
                </select>
                <Button onClick={() => removerMembro(m.id)} aria-label="Remover membro"><Trash2 size={14} /></Button>
              </div>
            </Card>
          ))
        )}
        <Card style={{ marginTop: 8, display: "flex", gap: 8, flexWrap: "wrap", alignItems: "flex-end" }}>
          <Field label="Nome">
            <input className="input" value={novoMembro.nome} onChange={(e) => setNovoMembro({ ...novoMembro, nome: e.target.value })} style={{ minWidth: 160 }} />
          </Field>
          <Field label="Papel">
            <input className="input" placeholder="mãe, ACS, psiquiatra…" value={novoMembro.papel} onChange={(e) => setNovoMembro({ ...novoMembro, papel: e.target.value })} style={{ minWidth: 140 }} />
          </Field>
          <Field label="Vínculo">
            <select className="input" value={novoMembro.tipo_vinculo} onChange={(e) => setNovoMembro({ ...novoMembro, tipo_vinculo: e.target.value })}>
              <option value="familiar">Familiar</option>
              <option value="comunitario">Comunitário</option>
              <option value="servico">Serviço</option>
              <option value="outro">Outro</option>
            </select>
          </Field>
          <Field label="Força">
            <select className="input" value={novoMembro.forca_vinculo} onChange={(e) => setNovoMembro({ ...novoMembro, forca_vinculo: e.target.value })}>
              <option value="forte">Forte</option>
              <option value="fragil">Frágil</option>
              <option value="conflito">Conflito</option>
            </select>
          </Field>
          <Button variant="primary" onClick={adicionarMembro} loading={addingMembro} disabled={!novoMembro.nome.trim()}>
            <UserPlus size={16} /> Adicionar
          </Button>
        </Card>

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
