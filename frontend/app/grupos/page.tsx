"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import { UsersRound, Plus } from "lucide-react";
import { api, ApiError, getToken } from "@/lib/api";
import { grupoTipoLabel } from "@/lib/labels";
import { dataCurtaComHora } from "@/lib/date";
import { plural } from "@/lib/format";
import { Topbar } from "@/components/Topbar";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Drawer } from "@/components/ui/Drawer";
import { Field } from "@/components/ui/Field";
import { EmptyState } from "@/components/ui/EmptyState";
import { Skeleton } from "@/components/ui/Skeleton";
import { SectionTitle } from "@/components/ui/SectionTitle";

type EncontroResumo = {
  id: string; tipo: string; titulo: string; data: string;
  local: string | null; total_participantes: number; presentes: number;
};

export default function GruposPage() {
  const router = useRouter();
  const [rows, setRows] = useState<EncontroResumo[]>([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [criando, setCriando] = useState(false);
  const [form, setForm] = useState({ tipo: "grupo", titulo: "", data: "", local: "", tema: "" });

  useEffect(() => {
    if (!getToken()) return void router.replace("/login");
    (async () => {
      try {
        setRows(await api<EncontroResumo[]>("/grupos"));
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
      const enc = await api<{ id: string }>("/grupos", {
        method: "POST",
        body: JSON.stringify({
          tipo: form.tipo,
          titulo: form.titulo,
          data: new Date(form.data).toISOString(),
          local: form.local.trim() || null,
          tema: form.tema.trim() || null,
        }),
      });
      toast.success("Encontro criado. Adicione os participantes.");
      router.push(`/grupos/${enc.id}`);
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
          <SectionTitle margin="0">Grupos, oficinas e assembleias</SectionTitle>
          <Button variant="primary" onClick={() => setOpen(true)}><Plus size={16} /> Novo encontro</Button>
        </div>
        <p style={{ color: "var(--muted)", fontSize: 13, marginBottom: 16 }}>
          Registre encontros coletivos com múltiplos participantes — pacientes do serviço
          e pessoas da comunidade.
        </p>

        {loading ? (
          <Skeleton />
        ) : rows.length === 0 ? (
          <EmptyState icone={<UsersRound size={28} />} frase="Nenhum encontro registrado ainda." />
        ) : (
          rows.map((e) => (
            <Card key={e.id} className="row-stack" style={{ marginBottom: 8, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div>
                <div style={{ fontWeight: 500 }}>
                  <span className="badge badge-info" style={{ marginRight: 8 }}>{grupoTipoLabel(e.tipo)}</span>
                  {e.titulo}
                </div>
                <div style={{ color: "var(--muted)", fontSize: 12, marginTop: 2 }}>
                  {dataCurtaComHora(e.data)}{e.local && ` · ${e.local}`} · {e.presentes}/{e.total_participantes} {plural(e.total_participantes, "presente", "presentes")}
                </div>
              </div>
              <Link href={`/grupos/${e.id}`} className="btn">Abrir</Link>
            </Card>
          ))
        )}
      </main>

      <Drawer open={open} title="Novo encontro" onClose={() => setOpen(false)}>
        <form onSubmit={criar} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <Field label="Tipo">
            <select className="input" value={form.tipo} onChange={(e) => setForm({ ...form, tipo: e.target.value })}>
              <option value="grupo">Grupo</option>
              <option value="oficina">Oficina</option>
              <option value="assembleia">Assembleia</option>
            </select>
          </Field>
          <Field label="Título">
            <input className="input" required value={form.titulo} onChange={(e) => setForm({ ...form, titulo: e.target.value })} />
          </Field>
          <Field label="Data e hora">
            <input className="input" type="datetime-local" required value={form.data} onChange={(e) => setForm({ ...form, data: e.target.value })} />
          </Field>
          <Field label="Local (opcional)">
            <input className="input" value={form.local} onChange={(e) => setForm({ ...form, local: e.target.value })} />
          </Field>
          <Field label="Tema (opcional)">
            <input className="input" value={form.tema} onChange={(e) => setForm({ ...form, tema: e.target.value })} />
          </Field>
          <Button type="submit" variant="primary" loading={criando} style={{ marginTop: 4 }}>Criar e adicionar participantes</Button>
        </form>
      </Drawer>
    </>
  );
}
