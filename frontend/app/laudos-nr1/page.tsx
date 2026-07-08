"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import { FileWarning, Plus } from "lucide-react";
import { api, ApiError, getToken } from "@/lib/api";
import { dataCurtaComHora } from "@/lib/date";
import { Topbar } from "@/components/Topbar";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Drawer } from "@/components/ui/Drawer";
import { Field } from "@/components/ui/Field";
import { EmptyState } from "@/components/ui/EmptyState";
import { Skeleton } from "@/components/ui/Skeleton";
import { SectionTitle } from "@/components/ui/SectionTitle";
import { StatusBadge } from "@/components/ui/StatusBadge";

type LaudoResumo = {
  id: string; organizacao: string; setor: string | null;
  data: string; status: string; fatores_alto: number;
};

export default function LaudosNR1Page() {
  const router = useRouter();
  const [rows, setRows] = useState<LaudoResumo[]>([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [criando, setCriando] = useState(false);
  const [form, setForm] = useState({ organizacao: "", setor: "", responsavel: "" });

  useEffect(() => {
    if (!getToken()) return void router.replace("/login");
    (async () => {
      try {
        setRows(await api<LaudoResumo[]>("/laudos-nr1"));
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) router.replace("/login");
        else toast.error(err instanceof ApiError ? err.message : "Falha ao carregar");
      } finally {
        setLoading(false);
      }
    })();
  }, [router]);

  async function criar(e: React.FormEvent) {
    e.preventDefault();
    setCriando(true);
    try {
      const l = await api<{ id: string }>("/laudos-nr1", {
        method: "POST",
        body: JSON.stringify({
          organizacao: form.organizacao, setor: form.setor.trim() || null,
          responsavel: form.responsavel.trim() || null,
        }),
      });
      router.push(`/laudos-nr1/${l.id}`);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Falha");
      setCriando(false);
    }
  }

  return (
    <>
      <Topbar />
      <main className="container-praxis">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12, gap: 8 }}>
          <SectionTitle margin="0">Laudos de risco psicossocial (NR-1)</SectionTitle>
          <Button variant="primary" onClick={() => setOpen(true)}><Plus size={16} /> Novo laudo</Button>
        </div>
        <p style={{ color: "var(--muted)", fontSize: 13, marginBottom: 16 }}>
          Avaliação de fatores de risco psicossocial de uma organização/setor, para subsidiar o
          Gerenciamento de Riscos Ocupacionais (GRO/PGR). Documento organizacional — não usa prontuário.
        </p>

        {loading ? (
          <Skeleton />
        ) : rows.length === 0 ? (
          <EmptyState icone={<FileWarning size={28} />} frase="Nenhum laudo criado ainda." />
        ) : (
          rows.map((l) => (
            <Card key={l.id} className="row-stack" style={{ marginBottom: 8, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div>
                <div style={{ fontWeight: 500 }}>{l.organizacao}{l.setor && <span style={{ color: "var(--muted)", fontWeight: 400 }}> · {l.setor}</span>}</div>
                <div style={{ color: "var(--muted)", fontSize: 12, display: "flex", alignItems: "center", gap: 8, marginTop: 2 }}>
                  <StatusBadge status={l.status} />
                  <span>{dataCurtaComHora(l.data)}</span>
                  {l.fatores_alto > 0 && <span className="badge badge-risk">{l.fatores_alto} fator(es) alto</span>}
                </div>
              </div>
              <Link href={`/laudos-nr1/${l.id}`} className="btn">Abrir</Link>
            </Card>
          ))
        )}
      </main>

      <Drawer open={open} title="Novo laudo NR-1" onClose={() => setOpen(false)}>
        <form onSubmit={criar} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <Field label="Organização">
            <input className="input" required value={form.organizacao} onChange={(e) => setForm({ ...form, organizacao: e.target.value })} />
          </Field>
          <Field label="Setor (opcional)">
            <input className="input" value={form.setor} onChange={(e) => setForm({ ...form, setor: e.target.value })} />
          </Field>
          <Field label="Responsável técnico (opcional)">
            <input className="input" placeholder="Nome e CRP" value={form.responsavel} onChange={(e) => setForm({ ...form, responsavel: e.target.value })} />
          </Field>
          <Button type="submit" variant="primary" loading={criando} style={{ marginTop: 4 }}>Criar e avaliar fatores</Button>
        </form>
      </Drawer>
    </>
  );
}
