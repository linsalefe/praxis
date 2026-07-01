"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { ShieldCheck, Upload } from "lucide-react";
import { api, ApiError, getToken } from "@/lib/api";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8040";

type Cert = {
  titular: string; emissor: string | null; validade_ate: string;
  criado_em: string; expirado: boolean;
};

export function CertificadoManager() {
  const [cert, setCert] = useState<Cert | null | undefined>(undefined); // undefined=carregando, null=nenhum
  const [file, setFile] = useState<File | null>(null);
  const [senha, setSenha] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api<Cert>("/assinatura/certificado")
      .then(setCert)
      .catch(() => setCert(null));
  }, []);

  async function enviar(e: React.FormEvent) {
    e.preventDefault();
    if (!file) { toast.error("Escolha o arquivo .pfx / .p12"); return; }
    if (!senha) { toast.error("Informe a senha do certificado"); return; }
    setBusy(true);
    try {
      // multipart: NÃO definir Content-Type (o browser define o boundary).
      const fd = new FormData();
      fd.append("arquivo", file);
      fd.append("senha", senha);
      const res = await fetch(`${API_BASE}/assinatura/certificado`, {
        method: "POST", headers: { Authorization: `Bearer ${getToken()}` }, body: fd,
      });
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        throw new Error((j as { detail?: string }).detail || `Falha (${res.status})`);
      }
      setCert(await res.json());
      setFile(null); setSenha("");
      toast.success("Certificado A1 cadastrado.");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Falha ao enviar certificado");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card" style={{ marginTop: 16 }}>
      <h2 style={{ fontSize: 16, margin: "0 0 8px", display: "flex", alignItems: "center", gap: 8 }}>
        <ShieldCheck size={18} color="var(--brand-2)" /> Certificado de assinatura (ICP-Brasil A1)
      </h2>

      {cert === undefined && <p style={{ color: "var(--muted)" }}>Carregando…</p>}
      {cert && (
        <div style={{ marginBottom: 12 }}>
          <div><b>Titular:</b> {cert.titular}</div>
          <div style={{ color: "var(--muted)", fontSize: 13 }}>
            Emissor: {cert.emissor || "—"} · válido até {new Date(cert.validade_ate).toLocaleDateString("pt-BR")}
            {cert.expirado && <span className="badge badge-warn" style={{ marginLeft: 6 }}>expirado</span>}
          </div>
        </div>
      )}
      {cert === null && (
        <p style={{ color: "var(--muted)", fontSize: 13 }}>Nenhum certificado cadastrado. Envie seu A1 (.pfx / .p12) para assinar com ICP-Brasil.</p>
      )}

      <form onSubmit={enviar} style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        <div>
          <label className="label">Arquivo do certificado (.pfx / .p12)</label>
          <input className="input" type="file" accept=".pfx,.p12" onChange={(e) => setFile(e.target.files?.[0] || null)} />
        </div>
        <div>
          <label className="label">Senha do certificado</label>
          <input className="input" type="password" value={senha} onChange={(e) => setSenha(e.target.value)} placeholder="••••••••" />
        </div>
        <button className="btn btn-primary" disabled={busy}>
          <Upload size={16} /> {busy ? "Enviando…" : cert ? "Substituir certificado" : "Enviar certificado"}
        </button>
      </form>

      <p style={{ color: "var(--muted)", fontSize: 11, marginTop: 10 }}>
        O arquivo é guardado <b>cifrado</b> em repouso e a <b>senha nunca é armazenada</b> — ela é solicitada a cada
        assinatura. Certificados <b>A3</b> (token/cartão) não são suportados (exigem assinatura no dispositivo).
      </p>
    </div>
  );
}
