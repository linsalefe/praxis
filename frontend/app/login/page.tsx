"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import { Eye, EyeOff, Info, LogIn, ShieldCheck } from "lucide-react";
import { api, saveToken, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";

type LoginResp = { access_token: string; mfa_required: boolean; scope: string };

// Contato de recuperação de senha (curto prazo — reset por e-mail é feature à parte).
const SUPORTE_EMAIL = "suporte@cenatsaudemental.com";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [mostrarSenha, setMostrarSenha] = useState(false);
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
    <main style={{ minHeight: "100dvh", display: "grid", placeItems: "center", padding: 16 }}>
      <div style={{ width: "100%", maxWidth: 420 }}>
        <Card>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
            <ShieldCheck size={22} color="var(--brand-2)" />
            <h1 style={{ margin: 0, fontSize: 20 }}>Práxis · CENAT</h1>
          </div>
          <p style={{ color: "var(--muted)", margin: "0 0 20px", fontSize: 14 }}>
            Copiloto clínico para novas abordagens em saúde mental.
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
            <div style={{ position: "relative" }}>
              <input
                id="senha" className="input" type={mostrarSenha ? "text" : "password"} required
                value={senha} onChange={(e) => setSenha(e.target.value)}
                autoComplete="current-password" minLength={8}
                aria-invalid={erro ? true : undefined}
                style={{ paddingRight: 44 }}
              />
              <button
                type="button"
                onClick={() => setMostrarSenha((v) => !v)}
                aria-label={mostrarSenha ? "Ocultar senha" : "Mostrar senha"}
                aria-pressed={mostrarSenha}
                style={{
                  position: "absolute", right: 8, top: "50%", transform: "translateY(-50%)",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  border: "none", background: "transparent", cursor: "pointer",
                  color: "var(--muted)", padding: 6,
                }}
              >
                {mostrarSenha ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
            {erro && (
              <p role="alert" style={{ color: "var(--danger)", fontSize: 13, margin: "8px 0 0" }}>{erro}</p>
            )}
            <div style={{ height: 20 }} />
            <Button variant="primary" type="submit" loading={loading}>
              <LogIn size={16} /> {loading ? "Entrando…" : "Entrar"}
            </Button>
          </form>
          <p style={{ fontSize: 13, margin: "14px 0 0" }}>
            <a className="link" href={`mailto:${SUPORTE_EMAIL}?subject=Recupera%C3%A7%C3%A3o%20de%20senha%20-%20Pr%C3%A1xis`}>
              Esqueci minha senha
            </a>
          </p>
          <hr className="divider" />
          <p style={{ fontSize: 13, color: "var(--muted)", margin: 0 }}>
            Não tem conta? <Link className="link" href="/registro">Cadastre-se</Link>.
          </p>
        </Card>
      </div>
    </main>
  );
}
