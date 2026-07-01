"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import { PlusCircle } from "lucide-react";
import { api, ApiError, getScope, getToken } from "@/lib/api";
import { Topbar } from "@/components/Topbar";

type Paciente = {
  id: string; nome: string; contato: string | null;
  nascimento: string | null; documento: string | null; sexo: string | null;
  criado_em: string; atualizado_em: string;
};
type Me = { nome: string };

export default function PacientesPage() {
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);
  const [rows, setRows] = useState<Paciente[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ nome: "", contato: "", nascimento: "", documento: "", sexo: "" });

  useEffect(() => {
    const t = getToken();
    if (!t) return void router.replace("/login");
    if (getScope() === "pre_2fa") return void router.replace("/login/2fa");
    (async () => {
      try {
        setMe(await api<Me>("/auth/me"));
        setRows(await api<Paciente[]>("/pacientes"));
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
    setCreating(true);
    try {
      const p = await api<Paciente>("/pacientes", {
        method: "POST",
        body: JSON.stringify({
          nome: form.nome,
          contato: form.contato || null,
          nascimento: form.nascimento || null,
          documento: form.documento || null,
          sexo: form.sexo || null,
        }),
      });
      setRows((r) => [p, ...r]);
      setForm({ nome: "", contato: "", nascimento: "", documento: "", sexo: "" });
      toast.success("Paciente criado.");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Falha ao criar");
    } finally {
      setCreating(false);
    }
  }

  return (
    <>
      <Topbar meNome={me?.nome} />
      <main className="container-praxis">
        <h1 style={{ fontSize: 22, margin: "8px 0 20px" }}>Pacientes</h1>

        <div className="card" style={{ marginBottom: 24 }}>
          <h2 style={{ fontSize: 15, margin: "0 0 12px", color: "var(--muted)" }}>Novo paciente</h2>
          <form onSubmit={criar} style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr 1fr 1fr auto", gap: 8, alignItems: "end" }}>
            <div><label className="label">Nome</label>
              <input className="input" required value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} /></div>
            <div><label className="label">Contato</label>
              <input className="input" value={form.contato} onChange={(e) => setForm({ ...form, contato: e.target.value })} /></div>
            <div><label className="label">Nascimento</label>
              <input className="input" type="date" value={form.nascimento} onChange={(e) => setForm({ ...form, nascimento: e.target.value })} /></div>
            <div><label className="label">Documento</label>
              <input className="input" value={form.documento} onChange={(e) => setForm({ ...form, documento: e.target.value })} /></div>
            <div><label className="label">Sexo</label>
              <input className="input" value={form.sexo} onChange={(e) => setForm({ ...form, sexo: e.target.value })} /></div>
            <button className="btn btn-primary" disabled={creating}>
              <PlusCircle size={16} /> {creating ? "..." : "Adicionar"}
            </button>
          </form>
        </div>

        {loading ? (
          <p style={{ color: "var(--muted)" }}>Carregando…</p>
        ) : rows.length === 0 ? (
          <p style={{ color: "var(--muted)" }}>Nenhum paciente cadastrado ainda.</p>
        ) : (
          <div className="card" style={{ padding: 0 }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ textAlign: "left", color: "var(--muted)", fontSize: 12 }}>
                  <th style={{ padding: 12 }}>Nome</th>
                  <th style={{ padding: 12 }}>Contato</th>
                  <th style={{ padding: 12 }}>Nascimento</th>
                  <th style={{ padding: 12 }}>Criado em</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((p) => (
                  <tr key={p.id} style={{ borderTop: "1px solid var(--border)" }}>
                    <td style={{ padding: 12 }}>
                      <Link className="link" href={`/pacientes/${p.id}`}>{p.nome}</Link>
                    </td>
                    <td style={{ padding: 12 }}>{p.contato || "—"}</td>
                    <td style={{ padding: 12 }}>{p.nascimento || "—"}</td>
                    <td style={{ padding: 12, color: "var(--muted)" }}>
                      {new Date(p.criado_em).toLocaleString("pt-BR")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </>
  );
}
