"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Info, KeyRound, LogOut, ShieldCheck } from "lucide-react";
import { api, ApiError, getToken, clearToken } from "@/lib/api";
import { Topbar } from "@/components/Topbar";
import { CertificadoManager } from "@/components/CertificadoManager";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Field } from "@/components/ui/Field";

type Me = { id: string; nome: string; email: string; totp_ativado: boolean };
type SetupResp = { otpauth_url: string; qrcode_data_uri: string };

export default function Conta2FA() {
  const router = useRouter();
  const [obrigatorio, setObrigatorio] = useState(false);
  const [me, setMe] = useState<Me | null>(null);
  const [setup, setSetup] = useState<SetupResp | null>(null);
  const [codigo, setCodigo] = useState("");

  useEffect(() => {
    if (new URLSearchParams(window.location.search).get("obrigatorio") === "1") setObrigatorio(true);
  }, []);

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
      if (obrigatorio) router.replace("/inicio");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Código inválido");
    }
  }

  async function encerrarTodasSessoes() {
    if (!window.confirm("Encerrar todas as sessões em todos os dispositivos? Você precisará entrar novamente.")) return;
    try {
      await api("/auth/sessoes/revogar-todas", { method: "POST" });
      clearToken();
      toast.success("Todas as sessões foram encerradas.");
      router.replace("/login");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Não foi possível encerrar as sessões.");
    }
  }

  if (!me) return (<><Topbar /><main className="container-praxis"><p style={{ color: "var(--muted)" }}>Carregando…</p></main></>);

  return (
    <>
      <Topbar meNome={me.nome} />
      <main className="container-praxis" style={{ maxWidth: 560 }}>
        <h1 style={{ fontSize: "var(--fs-xl)", margin: "8px 0 20px" }}>Autenticação em dois fatores</h1>
        {obrigatorio && !me.totp_ativado && (
          <div className="badge badge-warn" role="status" style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16, padding: "10px 14px" }}>
            <Info size={16} />
            <span>O 2FA é obrigatório para acessar dados clínicos. Conclua a configuração abaixo para continuar.</span>
          </div>
        )}
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

        <Card style={{ marginTop: 16 }}>
          <h2 style={{ fontSize: 15, margin: "0 0 6px", display: "flex", alignItems: "center", gap: 8 }}>
            <LogOut size={16} color="var(--muted)" /> Sessões
          </h2>
          <p style={{ margin: "0 0 12px", color: "var(--muted)", fontSize: 14 }}>
            Se você suspeitar de acesso indevido, encerre todas as sessões ativas — inclusive
            neste dispositivo. Você precisará entrar novamente.
          </p>
          <Button onClick={encerrarTodasSessoes}>
            <LogOut size={16} /> Encerrar todas as sessões
          </Button>
        </Card>

        <CertificadoManager />
      </main>
    </>
  );
}
