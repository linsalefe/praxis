"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import { LogIn, ShieldCheck } from "lucide-react";
import { api, saveToken, ApiError } from "@/lib/api";

type LoginResp = { access_token: string; mfa_required: boolean; scope: string };

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
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
      const msg = err instanceof ApiError ? err.message : "Falha no login";
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="container-praxis" style={{ maxWidth: 460 }}>
      <div className="card">
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
          <ShieldCheck size={22} color="var(--brand-2)" />
          <h1 style={{ margin: 0, fontSize: 20 }}>Práxis · CENAT</h1>
        </div>
        <p style={{ color: "var(--muted)", margin: "0 0 20px" }}>
          Entre com sua conta profissional.
        </p>
        <form onSubmit={onSubmit}>
          <label className="label" htmlFor="email">Email</label>
          <input
            id="email" className="input" type="email" required
            value={email} onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
          />
          <div style={{ height: 12 }} />
          <label className="label" htmlFor="senha">Senha</label>
          <input
            id="senha" className="input" type="password" required
            value={senha} onChange={(e) => setSenha(e.target.value)}
            autoComplete="current-password" minLength={8}
          />
          <div style={{ height: 20 }} />
          <button className="btn btn-primary" type="submit" disabled={loading}>
            <LogIn size={16} /> {loading ? "Entrando…" : "Entrar"}
          </button>
        </form>
        <hr className="divider" />
        <p style={{ fontSize: 13, color: "var(--muted)" }}>
          Não tem conta? <Link className="link" href="/registro">Cadastre-se</Link>.
        </p>
      </div>
    </main>
  );
}
