"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { KeyRound, ShieldCheck } from "lucide-react";
import { api, ApiError, getToken } from "@/lib/api";
import { Topbar } from "@/components/Topbar";
import { CertificadoManager } from "@/components/CertificadoManager";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Field } from "@/components/ui/Field";

type Me = { id: string; nome: string; email: string; totp_ativado: boolean };
type SetupResp = { otpauth_url: string; qrcode_data_uri: string };

export default function Conta2FA() {
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);
  const [setup, setSetup] = useState<SetupResp | null>(null);
  const [codigo, setCodigo] = useState("");

  useEffect(() => {
    if (!getToken()) return void router.replace("/login");
    (async () => {
      try { setMe(await api<Me>("/auth/me")); }
      catch (err) {
        if (err instanceof ApiError && err.status === 401) router.replace("/login");
      }
    })();
  }, [router]);

  async function iniciar() {
    try { setSetup(await api<SetupResp>("/auth/2fa/setup", { method: "POST" })); }
    catch (err) { toast.error(err instanceof ApiError ? err.message : "Falha"); }
  }

  async function confirmar() {
    try {
      const r = await api<Me>("/auth/2fa/verify", { method: "POST", body: JSON.stringify({ codigo }) });
      setMe(r);
      setSetup(null);
      setCodigo("");
      toast.success("2FA ativado.");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Código inválido");
    }
  }

  if (!me) return (<><Topbar /><main className="container-praxis"><p style={{ color: "var(--muted)" }}>Carregando…</p></main></>);

  return (
    <>
      <Topbar meNome={me.nome} />
      <main className="container-praxis" style={{ maxWidth: 560 }}>
        <h1 style={{ fontSize: 22, margin: "8px 0 20px" }}>Autenticação em dois fatores</h1>
        <Card>
          <p style={{ margin: 0, display: "flex", alignItems: "center", gap: 8 }}>
            <ShieldCheck size={18} color={me.totp_ativado ? "var(--ok)" : "var(--muted)"} />
            Status: <strong>{me.totp_ativado ? "Ativado" : "Não ativado"}</strong>
          </p>

          {!me.totp_ativado && !setup && (
            <>
              <p style={{ color: "var(--muted)" }}>
                Ative o 2FA para proteger o acesso a dados clínicos. Use um app como Aegis, Google Authenticator ou 1Password.
              </p>
              <Button variant="primary" onClick={iniciar}>
                <KeyRound size={16} /> Iniciar configuração
              </Button>
            </>
          )}

          {setup && (
            <>
              <p style={{ marginTop: 16 }}>Escaneie o QR no seu autenticador:</p>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={setup.qrcode_data_uri} alt="QR code TOTP" width={220} height={220} style={{ background: "white", padding: 8, borderRadius: 8 }} />
              <p style={{ color: "var(--muted)", fontSize: 12, marginTop: 8, fontFamily: "monospace" }}>
                Ou copie: {setup.otpauth_url}
              </p>
              <div style={{ display: "flex", gap: 8, alignItems: "end", marginTop: 16 }}>
                <Field label="Código de 6 dígitos" style={{ flex: 1 }}>
                  <input className="input" inputMode="numeric" autoComplete="one-time-code" maxLength={8} value={codigo}
                    onChange={(e) => setCodigo(e.target.value.replace(/\D/g, ""))}
                    style={{ fontFamily: "var(--font-mono)", letterSpacing: ".3em", textAlign: "center" }} />
                </Field>
                <Button variant="primary" onClick={confirmar}>Confirmar</Button>
              </div>
            </>
          )}
        </Card>

        <CertificadoManager />
      </main>
    </>
  );
}
