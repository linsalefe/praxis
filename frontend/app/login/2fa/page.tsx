"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { KeyRound } from "lucide-react";
import { api, saveToken, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";

type TokenResp = { access_token: string; scope: string };

export default function TwoFactorPage() {
  const router = useRouter();
  const [codigo, setCodigo] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      const data = await api<TokenResp>("/auth/2fa/login", {
        method: "POST",
        body: JSON.stringify({ codigo }),
      });
      saveToken(data.access_token, data.scope);
      toast.success("2FA verificado.");
      router.replace("/pacientes");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Código inválido");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="container-praxis" style={{ maxWidth: 420 }}>
      <Card>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
          <KeyRound size={22} color="var(--brand-2)" />
          <h1 style={{ margin: 0, fontSize: 20 }}>Verificação 2FA</h1>
        </div>
        <p style={{ color: "var(--muted)", margin: "0 0 20px" }}>
          Digite o código de 6 dígitos do seu autenticador.
        </p>
        <form onSubmit={onSubmit}>
          <input
            className="input"
            inputMode="numeric"
            pattern="[0-9]*"
            maxLength={8}
            minLength={6}
            required
            value={codigo}
            onChange={(e) => setCodigo(e.target.value.replace(/\D/g, ""))}
            autoFocus
          />
          <div style={{ height: 16 }} />
          <Button variant="primary" type="submit" loading={loading}>
            {loading ? "Verificando…" : "Verificar"}
          </Button>
        </form>
      </Card>
    </main>
  );
}
