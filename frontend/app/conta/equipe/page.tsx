"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { ShieldCheck, UserPlus, UsersRound } from "lucide-react";
import { api, ApiError, getToken } from "@/lib/api";
import { Topbar } from "@/components/Topbar";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Field } from "@/components/ui/Field";
import { Skeleton } from "@/components/ui/Skeleton";

type Me = { id: string; nome: string; papel: string };
type Membro = {
  id: string; nome: string; email: string; papel: string;
  crp: string | null; crp_verificado: boolean; totp_ativado: boolean;
};

const ABORDAGENS = [
  { v: "", l: "— (não definir)" },
  { v: "dialogo_aberto", l: "Diálogo Aberto" },
  { v: "ouvir_vozes", l: "Ouvir Vozes" },
  { v: "gam", l: "GAM" },
  { v: "ptmf", l: "PTMF" },
  { v: "wrap", l: "WRAP" },
  { v: "reducao_danos", l: "Redução de Danos" },
  { v: "outros", l: "Outros" },
];

const VAZIO = { nome: "", email: "", senha: "", crp: "", abordagem: "" };

export default function ContaEquipe() {
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);
  const [membros, setMembros] = useState<Membro[] | null>(null);
  const [form, setForm] = useState({ ...VAZIO });
  const [erro, setErro] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);

  function upd<K extends keyof typeof form>(k: K, v: string) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  useEffect(() => {
    if (!getToken()) return void router.replace("/login");
    (async () => {
      try {
        const m = await api<Me>("/auth/me");
        setMe(m);
        if (m.papel !== "owner") return; // não-owner: mostra aviso, não busca equipe
        setMembros(await api<Membro[]>("/equipe"));
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) router.replace("/login");
      }
    })();
  }, [router]);

  async function adicionar(e: React.FormEvent) {
    e.preventDefault();
    setErro(null);
    setSalvando(true);
    try {
      await api<Membro>("/equipe/profissionais", {
        method: "POST",
        body: JSON.stringify({
          nome: form.nome,
          email: form.email,
          senha: form.senha,
          crp: form.crp || null,
          abordagem: form.abordagem || null,
        }),
      });
      setForm({ ...VAZIO });
      setMembros(await api<Membro[]>("/equipe"));
      toast.success("Profissional adicionado. Compartilhe a senha inicial com ele(a).");
    } catch (err) {
      setErro(err instanceof ApiError ? err.message : "Não foi possível adicionar.");
    } finally {
      setSalvando(false);
    }
  }

  if (!me) return (
    <>
      <Topbar />
      <main className="container-praxis" style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <Skeleton height={28} width="40%" />
        <Skeleton height={160} radius="var(--radius-lg)" />
      </main>
    </>
  );

  if (me.papel !== "owner") return (
    <>
      <Topbar meNome={me.nome} />
      <main className="container-praxis" style={{ maxWidth: 560 }}>
        <h1 style={{ fontSize: "var(--fs-xl)", margin: "8px 0 6px", display: "flex", alignItems: "center", gap: 8 }}>
          <UsersRound size={20} /> Equipe
        </h1>
        <Card>
          <p style={{ margin: 0, color: "var(--muted)" }}>
            A gestão de equipe é exclusiva do responsável (owner) da clínica.
          </p>
        </Card>
      </main>
    </>
  );

  return (
    <>
      <Topbar meNome={me.nome} />
      <main className="container-praxis" style={{ maxWidth: 720 }}>
        <h1 style={{ fontSize: "var(--fs-xl)", margin: "8px 0 6px", display: "flex", alignItems: "center", gap: 8 }}>
          <UsersRound size={20} /> Equipe
        </h1>
        <p style={{ color: "var(--muted)", marginTop: 0 }}>
          Adicione profissionais à sua clínica. Cada profissional enxerga apenas os
          próprios pacientes; você (responsável) enxerga todos.
        </p>

        <Card style={{ marginBottom: 16 }}>
          <h2 style={{ fontSize: 16, marginTop: 0, display: "flex", alignItems: "center", gap: 8 }}>
            <UserPlus size={16} color="var(--brand-2)" /> Adicionar profissional
          </h2>
          <form onSubmit={adicionar} style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <Field label="Nome completo">
              <input className="input" required minLength={2} value={form.nome} onChange={(e) => upd("nome", e.target.value)} />
            </Field>
            <Field label="Email">
              <input className="input" type="email" required value={form.email} onChange={(e) => upd("email", e.target.value)} />
            </Field>
            <Field label="Senha inicial (mín. 8)">
              <input className="input" type="password" required minLength={8} value={form.senha} onChange={(e) => upd("senha", e.target.value)} />
            </Field>
            <Field label="CRP (opcional)">
              <input className="input" placeholder="00/00000" value={form.crp} onChange={(e) => upd("crp", e.target.value)} />
            </Field>
            <Field label="Abordagem (opcional)">
              <select className="input" value={form.abordagem} onChange={(e) => upd("abordagem", e.target.value)}>
                {ABORDAGENS.map((a) => <option key={a.v} value={a.v}>{a.l}</option>)}
              </select>
            </Field>
            <div style={{ gridColumn: "1 / span 2", display: "flex", alignItems: "center", gap: 12 }}>
              <Button variant="primary" type="submit" disabled={salvando}>
                <UserPlus size={16} /> {salvando ? "Adicionando…" : "Adicionar"}
              </Button>
              <span style={{ fontSize: 12, color: "var(--muted)" }}>
                O profissional entra com a senha inicial e configura o 2FA no primeiro acesso.
              </span>
            </div>
            {erro && <p role="alert" style={{ gridColumn: "1 / span 2", color: "var(--danger)", fontSize: 13, margin: 0 }}>{erro}</p>}
          </form>
        </Card>

        <Card>
          <h2 style={{ fontSize: 16, marginTop: 0 }}>Membros</h2>
          {!membros ? (
            <Skeleton height={80} radius="var(--radius-md)" />
          ) : membros.length === 0 ? (
            <p style={{ margin: 0, color: "var(--muted)", fontSize: 14 }}>
              Nenhum membro ainda — adicione o primeiro profissional acima.
            </p>
          ) : (
            <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: 8 }}>
              {membros.map((m) => (
                <li key={m.id} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, padding: "10px 12px", border: "1px solid var(--border)", borderRadius: "var(--radius-md)" }}>
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontWeight: 600, display: "flex", alignItems: "center", gap: 8 }}>
                      <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{m.nome}</span>
                      <span className="badge">{m.papel === "owner" ? "responsável" : "profissional"}</span>
                    </div>
                    <div style={{ fontSize: 13, color: "var(--muted)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {m.email}{m.crp ? ` · CRP ${m.crp}` : ""}
                    </div>
                  </div>
                  <span title={m.totp_ativado ? "2FA ativo" : "2FA pendente"} style={{ display: "inline-flex", alignItems: "center", gap: 4, fontSize: 12, color: m.totp_ativado ? "var(--ok)" : "var(--muted)", flexShrink: 0 }}>
                    <ShieldCheck size={15} /> {m.totp_ativado ? "2FA" : "2FA pendente"}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </main>
    </>
  );
}
