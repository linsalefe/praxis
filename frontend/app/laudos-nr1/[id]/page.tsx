"use client";

import { useEffect, useState, use } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import { CheckCircle2, Save } from "lucide-react";
import { api, ApiError, getToken } from "@/lib/api";
import { dataCurtaComHora } from "@/lib/date";
import { Topbar } from "@/components/Topbar";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Field } from "@/components/ui/Field";
import { Skeleton } from "@/components/ui/Skeleton";
import { SectionTitle } from "@/components/ui/SectionTitle";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Segmented } from "@/components/ui/Segmented";

type Fator = { id: string; titulo: string; descricao: string };
type Nivel = "na" | "baixo" | "medio" | "alto";
type FatorAvaliado = { nivel: Nivel; observacao: string | null };
type Laudo = {
  id: string; organizacao: string; setor: string | null; data: string;
  fatores: Record<string, FatorAvaliado>; analise: string | null;
  recomendacoes: string | null; responsavel: string | null;
  status: string; finalizado_em: string | null; criado_em: string;
};

const NIVEL_OPCOES: { value: Nivel; label: string }[] = [
  { value: "na", label: "N/A" }, { value: "baixo", label: "Baixo" },
  { value: "medio", label: "Médio" }, { value: "alto", label: "Alto" },
];

export default function LaudoNR1Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const [laudo, setLaudo] = useState<Laudo | null>(null);
  const [fatoresDef, setFatoresDef] = useState<Fator[]>([]);
  const [fatores, setFatores] = useState<Record<string, FatorAvaliado>>({});
  const [campos, setCampos] = useState({ organizacao: "", setor: "", responsavel: "", analise: "", recomendacoes: "" });
  const [loading, setLoading] = useState(true);
  const [salvando, setSalvando] = useState(false);

  async function carregar() {
    const [l, def] = await Promise.all([
      api<Laudo>(`/laudos-nr1/${id}`),
      api<{ fatores: Fator[] }>(`/laudos-nr1/definicao`),
    ]);
    setLaudo(l);
    setFatoresDef(def.fatores);
    setFatores(l.fatores || {});
    setCampos({
      organizacao: l.organizacao, setor: l.setor || "", responsavel: l.responsavel || "",
      analise: l.analise || "", recomendacoes: l.recomendacoes || "",
    });
  }

  useEffect(() => {
    if (!getToken()) return void router.replace("/login");
    (async () => {
      try {
        await carregar();
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) router.replace("/login");
        else toast.error(err instanceof ApiError ? err.message : "Falha ao carregar");
      } finally {
        setLoading(false);
      }
    })();
  }, [id, router]);

  const finalizado = laudo?.status === "finalizado";

  function setNivel(fatorId: string, nivel: Nivel) {
    setFatores((f) => ({ ...f, [fatorId]: { nivel, observacao: f[fatorId]?.observacao ?? null } }));
  }
  function setObs(fatorId: string, observacao: string) {
    setFatores((f) => ({ ...f, [fatorId]: { nivel: f[fatorId]?.nivel ?? "na", observacao } }));
  }

  async function salvar() {
    setSalvando(true);
    try {
      const l = await api<Laudo>(`/laudos-nr1/${id}`, {
        method: "PATCH",
        body: JSON.stringify({
          organizacao: campos.organizacao, setor: campos.setor.trim() || null,
          responsavel: campos.responsavel.trim() || null,
          analise: campos.analise.trim() || null, recomendacoes: campos.recomendacoes.trim() || null,
          fatores,
        }),
      });
      setLaudo(l);
      toast.success("Laudo salvo.");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Falha ao salvar");
    } finally {
      setSalvando(false);
    }
  }

  async function finalizar() {
    try {
      const l = await api<Laudo>(`/laudos-nr1/${id}/finalizar`, { method: "POST" });
      setLaudo(l);
      toast.success("Laudo finalizado.");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Falha");
    }
  }

  if (loading) return (<><Topbar /><main className="container-praxis"><Skeleton /></main></>);
  if (!laudo) return null;

  return (
    <>
      <Topbar />
      <main className="container-praxis">
        <p style={{ margin: "0 0 12px" }}><Link className="link" href="/laudos-nr1">← Laudos NR-1</Link></p>

        <Card>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
            <StatusBadge status={laudo.status} />
            <span style={{ color: "var(--muted)", fontSize: 12 }}>{dataCurtaComHora(laudo.data)}</span>
          </div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <Field label="Organização">
              <input className="input" disabled={finalizado} value={campos.organizacao} onChange={(e) => setCampos({ ...campos, organizacao: e.target.value })} />
            </Field>
            <Field label="Setor">
              <input className="input" disabled={finalizado} value={campos.setor} onChange={(e) => setCampos({ ...campos, setor: e.target.value })} />
            </Field>
            <Field label="Responsável técnico">
              <input className="input" disabled={finalizado} value={campos.responsavel} onChange={(e) => setCampos({ ...campos, responsavel: e.target.value })} />
            </Field>
          </div>
        </Card>

        <SectionTitle margin="20px 0 8px">Fatores de risco psicossocial</SectionTitle>
        {fatoresDef.map((f) => (
          <Card key={f.id} style={{ marginBottom: 8 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12, flexWrap: "wrap" }}>
              <div style={{ flex: 1, minWidth: 200 }}>
                <div style={{ fontWeight: 600, fontSize: 14 }}>{f.titulo}</div>
                <div style={{ color: "var(--muted)", fontSize: 12 }}>{f.descricao}</div>
              </div>
              {finalizado ? (
                <StatusBadge status={`nivel_${fatores[f.id]?.nivel ?? "na"}`} />
              ) : (
                <Segmented<Nivel>
                  label={f.titulo}
                  value={fatores[f.id]?.nivel ?? "na"}
                  options={NIVEL_OPCOES}
                  onChange={(v) => setNivel(f.id, v)}
                />
              )}
            </div>
            <textarea
              className="input"
              rows={2}
              placeholder="Observação (opcional)"
              disabled={finalizado}
              style={{ marginTop: 8 }}
              value={fatores[f.id]?.observacao ?? ""}
              onChange={(e) => setObs(f.id, e.target.value)}
            />
          </Card>
        ))}

        <SectionTitle margin="20px 0 8px">Análise e recomendações</SectionTitle>
        <Field label="Análise">
          <textarea className="input" rows={4} disabled={finalizado} value={campos.analise} onChange={(e) => setCampos({ ...campos, analise: e.target.value })} />
        </Field>
        <div style={{ marginTop: 12 }}>
          <Field label="Recomendações para o GRO/PGR">
            <textarea className="input" rows={4} disabled={finalizado} value={campos.recomendacoes} onChange={(e) => setCampos({ ...campos, recomendacoes: e.target.value })} />
          </Field>
        </div>

        {!finalizado && (
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 16 }}>
            <Button onClick={salvar} loading={salvando}><Save size={16} /> Salvar</Button>
            <Button variant="primary" onClick={finalizar}><CheckCircle2 size={16} /> Finalizar laudo</Button>
          </div>
        )}
        {finalizado && (
          <p style={{ color: "var(--muted)", fontSize: 12, marginTop: 12 }}>
            Laudo finalizado em {laudo.finalizado_em && dataCurtaComHora(laudo.finalizado_em)} — não editável.
          </p>
        )}
      </main>
    </>
  );
}
