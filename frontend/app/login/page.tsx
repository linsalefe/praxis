"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import { Info, LogIn, ShieldCheck } from "lucide-react";
import { api, saveToken, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";

type LoginResp = { access_token: string; mfa_required: boolean; scope: string };

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [expirada, setExpirada] = useState(false);

  // U3: aviso de sessão expirada vindo do interceptor 401 (?expirada=1).
  useEffect(() => {
    if (new URLSearchParams(window.location.search).get("expirada") === "1") setExpirada(true);
  }, []);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setErro(null);
    try {
      const data = await api<LoginResp>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, senha }),
      });
      saveToken(data.access_token, data.scope);
      if (data.mfa_required) {
        router.replace("/login/2fa");
      } else {
        toast.success("Login realizado.");
        router.replace("/pacientes");
      }
    } catch (err) {
      // Credenciais/validação → erro inline; falha de rede → toast.
      if (err instanceof ApiError) setErro("E-mail ou senha incorretos.");
      else toast.error("Falha de conexão. Tente novamente.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="container-praxis" style={{ maxWidth: 460 }}>
      <Card>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
          <ShieldCheck size={22} color="var(--brand-2)" />
          <h1 style={{ margin: 0, fontSize: 20 }}>Práxis · CENAT</h1>
        </div>
        <p style={{ color: "var(--muted)", margin: "0 0 20px" }}>
          Entre com sua conta profissional.
        </p>
        {expirada && (
          <div className="badge badge-warn" role="status" style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 16, padding: "8px 12px" }}>
            <Info size={14} /> Sua sessão expirou. Entre novamente.
          </div>
        )}
        <form onSubmit={onSubmit} noValidate>
          <label className="label" htmlFor="email">Email</label>
          <input
            id="email" className="input" type="email" required
            value={email} onChange={(e) => setEmail(e.target.value)}
            autoComplete="email" aria-invalid={erro ? true : undefined}
          />
          <div style={{ height: 12 }} />
          <label className="label" htmlFor="senha">Senha</label>
          <input
            id="senha" className="input" type="password" required
            value={senha} onChange={(e) => setSenha(e.target.value)}
            autoComplete="current-password" minLength={8}
            aria-invalid={erro ? true : undefined}
          />
          {erro && (
            <p role="alert" style={{ color: "var(--danger)", fontSize: 13, margin: "8px 0 0" }}>{erro}</p>
          )}
          <div style={{ height: 20 }} />
          <Button variant="primary" type="submit" loading={loading}>
            <LogIn size={16} /> {loading ? "Entrando…" : "Entrar"}
          </Button>
        </form>
        <hr className="divider" />
        <p style={{ fontSize: 13, color: "var(--muted)" }}>
          Não tem conta? <Link className="link" href="/registro">Cadastre-se</Link>.
        </p>
      </Card>
    </main>
  );
}
