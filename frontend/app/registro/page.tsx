"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import { UserPlus } from "lucide-react";
import { api, saveToken, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Field } from "@/components/ui/Field";

const ABORDAGENS = [
  { v: "dialogo_aberto", l: "Diálogo Aberto" },
  { v: "ouvir_vozes", l: "Ouvir Vozes" },
  { v: "gam", l: "GAM (Gestão Autônoma da Medicação)" },
  { v: "ptmf", l: "PTMF" },
  { v: "wrap", l: "WRAP" },
  { v: "reducao_danos", l: "Redução de Danos" },
  { v: "outros", l: "Outros" },
];

export default function RegisterPage() {
  const router = useRouter();
  const [form, setForm] = useState({
    nome: "", email: "", senha: "", crp: "",
    abordagem: "dialogo_aberto", tenant_tipo: "solo", tenant_nome: "",
  });
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  function upd<K extends keyof typeof form>(k: K, v: string) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  const emailInvalido = !!erro && /e-?mail/i.test(erro);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setErro(null);
    try {
      const data = await api<{ access_token: string; scope: string }>("/auth/register", {
        method: "POST",
        body: JSON.stringify(form),
      });
      saveToken(data.access_token, data.scope);
      toast.success("Cadastro concluído. Configure o 2FA para continuar.");
      router.replace("/conta/2fa?obrigatorio=1");
    } catch (err) {
      if (err instanceof ApiError) setErro(err.message);
      else toast.error("Falha de conexão. Tente novamente.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="container-praxis" style={{ maxWidth: 560 }}>
      <Card>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
          <UserPlus size={22} color="var(--brand-2)" />
          <h1 style={{ margin: 0, fontSize: "var(--fs-xl)" }}>Cadastro profissional</h1>
        </div>
        <p style={{ color: "var(--muted)", margin: "0 0 20px" }}>
          Isso cria o espaço do seu consultório no Práxis.
        </p>
        <form onSubmit={onSubmit}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <Field label="Nome completo">
              <input className="input" required value={form.nome} onChange={(e) => upd("nome", e.target.value)} />
            </Field>
            <Field label="CRP">
              <input className="input" placeholder="00/00000" value={form.crp} onChange={(e) => upd("crp", e.target.value)} />
            </Field>
            <Field label="Email">
              <input className="input" type="email" required value={form.email} onChange={(e) => upd("email", e.target.value)} aria-invalid={emailInvalido || undefined} />
            </Field>
            <Field label="Senha (mín. 8)">
              <input className="input" type="password" required minLength={8} value={form.senha} onChange={(e) => upd("senha", e.target.value)} />
            </Field>
            <Field label="Abordagem preferida">
              <select
                className="input"
                value={form.abordagem}
                onChange={(e) => upd("abordagem", e.target.value)}
              >
                {ABORDAGENS.map((a) => (
                  <option key={a.v} value={a.v}>{a.l}</option>
                ))}
              </select>
            </Field>
            <Field label="Você atende em…">
              <select
                className="input"
                value={form.tenant_tipo}
                onChange={(e) => upd("tenant_tipo", e.target.value)}
              >
                <option value="solo">Consultório individual</option>
                <option value="clinica">Clínica</option>
              </select>
            </Field>
            <Field label="Nome do consultório/clínica" style={{ gridColumn: "1 / span 2" }}>
              <input className="input" required value={form.tenant_nome} onChange={(e) => upd("tenant_nome", e.target.value)} />
            </Field>
          </div>
          {erro && (
            <p role="alert" style={{ color: "var(--danger)", fontSize: 13, margin: "12px 0 0" }}>{erro}</p>
          )}
          <div style={{ height: 16 }} />
          <Button variant="primary" type="submit" loading={loading}>
            {loading ? "Cadastrando…" : "Cadastrar"}
          </Button>
        </form>
        <hr className="divider" />
        <p style={{ fontSize: 13, color: "var(--muted)" }}>
          Já tem conta? <Link className="link" href="/login">Entrar</Link>.
        </p>
      </Card>
    </main>
  );
}
