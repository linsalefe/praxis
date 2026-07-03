"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import { PlusCircle, Search, Users } from "lucide-react";
import { api, ApiError, getScope, getToken } from "@/lib/api";
import { dataRelativa } from "@/lib/date";
import { formatNome } from "@/lib/format";
import { Topbar } from "@/components/Topbar";
import { Skeleton } from "@/components/ui/Skeleton";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Field } from "@/components/ui/Field";
import { EmptyState } from "@/components/ui/EmptyState";
import { Drawer } from "@/components/ui/Drawer";

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
  const [drawer, setDrawer] = useState(false);
  const [busca, setBusca] = useState("");
  const [erroCriar, setErroCriar] = useState<string | null>(null);
  const [generoCustom, setGeneroCustom] = useState(false);
  const [form, setForm] = useState({ nome: "", contato: "", nascimento: "", documento: "", sexo: "" });
  const buscaRef = useRef<HTMLInputElement>(null);

  // U12: "/" foca a busca (fora de campos de texto); Esc limpa.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const alvo = e.target as HTMLElement | null;
      const digitando = alvo && (alvo.tagName === "INPUT" || alvo.tagName === "TEXTAREA" || alvo.tagName === "SELECT" || alvo.isContentEditable);
      if (e.key === "/" && !digitando) {
        e.preventDefault();
        buscaRef.current?.focus();
      } else if (e.key === "Escape" && alvo === buscaRef.current) {
        setBusca("");
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    const t = getToken();
    if (!t) return void router.replace("/login");
    if (getScope() === "pre_2fa") return void router.replace("/login/2fa");
    if (new URLSearchParams(window.location.search).get("novo") === "1") setDrawer(true);
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

  const filtrados = useMemo(() => {
    const q = busca.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter(
      (p) => p.nome.toLowerCase().includes(q) || (p.contato || "").toLowerCase().includes(q),
    );
  }, [rows, busca]);

  async function criar(e: React.FormEvent) {
    e.preventDefault();
    setCreating(true);
    setErroCriar(null);
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
      setGeneroCustom(false);
      setDrawer(false);
      toast.success("Paciente criado.");
    } catch (err) {
      if (err instanceof ApiError) setErroCriar(err.message);
      else toast.error("Falha de conexão. Tente novamente.");
    } finally {
      setCreating(false);
    }
  }

  return (
    <>
      <Topbar meNome={me?.nome} />
      <main className="container-praxis">
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, margin: "8px 0 20px" }}>
          <h1 style={{ fontSize: "var(--fs-xl)", margin: 0 }}>Pacientes</h1>
          <Button variant="primary" onClick={() => setDrawer(true)}>
            <PlusCircle size={16} /> Novo paciente
          </Button>
        </div>

        {/* Busca */}
        <div style={{ position: "relative", marginBottom: 16, maxWidth: 420 }}>
          <Search size={16} color="var(--muted)" style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)" }} />
          <input
            ref={buscaRef}
            className="input"
            style={{ paddingLeft: 36 }}
            placeholder="Buscar por nome ou contato…  ( / )"
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
          />
        </div>

        {loading ? (
          <Card style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} height={20} width={`${90 - i * 8}%`} />)}
          </Card>
        ) : rows.length === 0 ? (
          <EmptyState
            icone={<Users size={28} />}
            frase="Nenhum paciente cadastrado ainda."
            cta={<Button variant="primary" onClick={() => setDrawer(true)}><PlusCircle size={16} /> Novo paciente</Button>}
          />
        ) : filtrados.length === 0 ? (
          <p style={{ color: "var(--muted)" }}>Nenhum paciente encontrado para “{busca}”.</p>
        ) : (
          <Card style={{ padding: 0 }}>
            <table className="table-cards" style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ textAlign: "left", color: "var(--muted)", fontSize: 12 }}>
                  <th style={{ padding: 12 }}>Nome</th>
                  <th style={{ padding: 12 }}>Contato</th>
                  <th style={{ padding: 12 }}>Nascimento</th>
                  <th style={{ padding: 12 }}>Criado em</th>
                </tr>
              </thead>
              <tbody>
                {filtrados.map((p) => (
                  <tr key={p.id} style={{ borderTop: "1px solid var(--border)" }}>
                    <td data-label="Nome" style={{ padding: 12 }}>
                      <Link className="link" href={`/pacientes/${p.id}`}>{formatNome(p.nome)}</Link>
                    </td>
                    <td data-label="Contato" style={{ padding: 12 }}>{p.contato || "—"}</td>
                    <td data-label="Nascimento" style={{ padding: 12 }}>{p.nascimento || "—"}</td>
                    <td data-label="Criado em" style={{ padding: 12, color: "var(--muted)" }}>
                      {dataRelativa(p.criado_em)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        )}
      </main>

      {/* Drawer — Novo paciente */}
      {drawer && (
        <Drawer open title="Novo paciente" onClose={() => { if (!creating) setDrawer(false); }}>
          <form onSubmit={criar} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <Field label="Nome *">
              <input className="input" required value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} />
            </Field>
            <Field label="Contato">
              <input className="input" value={form.contato} onChange={(e) => setForm({ ...form, contato: e.target.value })} />
            </Field>
            <Field label="Nascimento">
              <input className="input" type="date" value={form.nascimento} onChange={(e) => setForm({ ...form, nascimento: e.target.value })} />
            </Field>
            <Field label="Documento">
              <input className="input" value={form.documento} onChange={(e) => setForm({ ...form, documento: e.target.value })} />
            </Field>
            <Field label="Gênero">
              <select
                className="input"
                value={generoCustom ? "__custom__" : form.sexo}
                onChange={(e) => {
                  if (e.target.value === "__custom__") { setGeneroCustom(true); setForm({ ...form, sexo: "" }); }
                  else { setGeneroCustom(false); setForm({ ...form, sexo: e.target.value }); }
                }}
              >
                <option value="">—</option>
                <option value="Mulher">Mulher</option>
                <option value="Homem">Homem</option>
                <option value="Não binário">Não binário</option>
                <option value="Prefiro não informar">Prefiro não informar</option>
                <option value="__custom__">Autodescrever…</option>
              </select>
              {generoCustom && (
                <input
                  className="input"
                  style={{ marginTop: 8 }}
                  placeholder="Como você se descreve"
                  value={form.sexo}
                  onChange={(e) => setForm({ ...form, sexo: e.target.value })}
                />
              )}
            </Field>
            {/* Y17: erro geral do formulário — separado da validação de campo. */}
            {erroCriar && (
              <p role="alert" style={{ color: "var(--danger)", fontSize: 13, margin: 0 }}>{erroCriar}</p>
            )}
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 8 }}>
              <Button type="button" onClick={() => setDrawer(false)} disabled={creating}>Cancelar</Button>
              <Button type="submit" variant="primary" loading={creating}>
                <PlusCircle size={16} /> {creating ? "Adicionando…" : "Adicionar"}
              </Button>
            </div>
          </form>
        </Drawer>
      )}
    </>
  );
}
