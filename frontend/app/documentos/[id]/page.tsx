"use client";

import { useEffect, useRef, useState, use } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import { BadgeCheck, Download, FileCheck2, FileSignature, RefreshCcw, ShieldCheck } from "lucide-react";
import { api, ApiError, getToken } from "@/lib/api";
import { Topbar } from "@/components/Topbar";
import { Drawer } from "@/components/ui/Drawer";
import { CopiarBtn } from "@/components/ui/CopiarBtn";
import { BreadcrumbPaciente } from "@/components/ui/BreadcrumbPaciente";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Field } from "@/components/ui/Field";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8040";

type Template = {
  tipo: string; titulo: string; descricao: string;
  blocos: { id: string; label: string; hint: string; palavras_alvo: [number, number] }[];
};
type Doc = {
  id: string; paciente_id: string; autor_id: string;
  tipo: string; finalidade: string; destinatario: string | null;
  conteudo: Record<string, string>; status: "rascunho" | "assinado";
  provider: string | null; prompt_versao: string | null;
  assinado_em: string | null; hash_assinatura: string | null;
  anexo_pdf_id: string | null;
  assinatura_tipo: string; cert_titular: string | null;
  criado_em: string; atualizado_em: string;
  aviso: string;
};
type Verificacao = {
  assinatura_tipo: string; assinado: boolean;
  intacto: boolean | null; valido: boolean | null; confiavel: boolean | null;
  titular: string | null; algoritmo: string | null; nota: string | null;
};
// Metadados do certificado A1 (GET /assinatura/certificado, 404 se não houver).
type Cert = { titular: string; validade_ate: string; expirado: boolean };

export default function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const [doc, setDoc] = useState<Doc | null>(null);
  const [tpl, setTpl] = useState<Template | null>(null);
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [icpOpen, setIcpOpen] = useState(false);
  const [senhaIcp, setSenhaIcp] = useState("");
  const [verif, setVerif] = useState<Verificacao | null>(null);
  const [cert, setCert] = useState<Cert | null>(null);
  const [confirmAssinar, setConfirmAssinar] = useState(false);
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!getToken()) return void router.replace("/login");
    (async () => {
      try {
        const d = await api<Doc>(`/documentos/${id}`);
        setDoc(d);
        const templates = await api<Template[]>("/documentos/templates");
        setTpl(templates.find((t) => t.tipo === d.tipo) || null);
        if (d.assinatura_tipo === "icp_brasil") {
          api<Verificacao>(`/documentos/${id}/assinatura`).then(setVerif).catch(() => {});
        }
        // Só enquanto rascunho: se houver A1 válido, a UI prioriza o ICP-Brasil.
        if (d.status !== "assinado") {
          api<Cert>("/assinatura/certificado").then(setCert).catch(() => {});
        }
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) router.replace("/login");
        else toast.error(err instanceof ApiError ? err.message : "Erro");
      }
    })();
  }, [id, router]);

  const scheduleSave = () => {
    setDirty(true);
    if (saveTimer.current) clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(salvar, 800);
  };

  async function salvar() {
    if (!doc) return;
    try {
      const d = await api<Doc>(`/documentos/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ conteudo: doc.conteudo, finalidade: doc.finalidade, destinatario: doc.destinatario || "" }),
      });
      setDoc(d);
      setDirty(false);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Falha ao salvar");
    }
  }

  async function assinar() {
    if (!doc) return;
    if (dirty) await salvar();
    setBusy("Assinando…");
    try {
      const d = await api<Doc>(`/documentos/${id}/assinar`, { method: "POST" });
      setDoc(d);
      setConfirmAssinar(false);
      toast.success("Documento assinado e anexado ao prontuário.");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Falha ao assinar");
    } finally {
      setBusy(null);
    }
  }

  async function assinarIcp() {
    if (!doc || !senhaIcp) { toast.error("Informe a senha do certificado."); return; }
    if (dirty) await salvar();
    setBusy("Assinando com ICP-Brasil…");
    try {
      const d = await api<Doc>(`/documentos/${id}/assinar-icp`, {
        method: "POST", body: JSON.stringify({ senha: senhaIcp }),
      });
      setDoc(d);
      setIcpOpen(false);
      setSenhaIcp("");
      toast.success("Documento assinado com ICP-Brasil (PAdES).");
      api<Verificacao>(`/documentos/${id}/assinatura`).then(setVerif).catch(() => {});
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Falha ao assinar");
    } finally {
      setBusy(null);
    }
  }

  if (!doc || !tpl) return (
    <><Topbar /><main className="container-praxis"><p style={{ color: "var(--muted)" }}>Carregando…</p></main></>
  );

  const finalizado = doc.status === "assinado";
  const temCertValido = !!cert && !cert.expirado;

  return (
    <>
      <Topbar />
      <main className="container-praxis" style={{ maxWidth: 880 }}>
        <BreadcrumbPaciente pacienteId={doc.paciente_id} />
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: 8 }}>
          <h1 style={{ fontSize: 22, margin: 0, display: "flex", alignItems: "center", gap: 8 }}>
            <FileSignature size={20} color="var(--brand-2)" /> {tpl.titulo}
          </h1>
          <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
            <CopiarBtn
              className="btn btn-ghost"
              texto={tpl.blocos.map((b) => `${b.label}\n${doc.conteudo[b.id] || ""}`).join("\n\n")}
            />
            {finalizado && (
              <span className={`badge ${doc.assinatura_tipo === "icp_brasil" ? "badge-pos" : "badge-neutral"}`}>
                {doc.assinatura_tipo === "icp_brasil" ? "ICP-Brasil" : "assinatura simples"}
              </span>
            )}
            <span className="badge">
              {finalizado ? "assinado" : "rascunho"}{dirty ? " · salvando…" : ""}
            </span>
          </div>
        </div>
        <p style={{ color: "var(--muted)", fontSize: 13, margin: "4px 0 12px" }}>{tpl.descricao}</p>

        <Card>
          <label className="label">Finalidade</label>
          <input
            className="input"
            value={doc.finalidade}
            onChange={(e) => { setDoc({ ...doc, finalidade: e.target.value }); scheduleSave(); }}
            disabled={finalizado}
          />
          {(doc.tipo === "encaminhamento" || doc.destinatario) && (
            <>
              <div style={{ height: 8 }} />
              <label className="label">Destinatário</label>
              <input
                className="input"
                value={doc.destinatario || ""}
                onChange={(e) => { setDoc({ ...doc, destinatario: e.target.value }); scheduleSave(); }}
                disabled={finalizado}
              />
            </>
          )}
        </Card>

        <div style={{ display: "flex", flexDirection: "column", gap: 12, marginTop: 12 }}>
          {tpl.blocos.map((b) => (
            <Card key={b.id}>
              <label className="label" style={{ fontSize: 14, color: "var(--text)", marginBottom: 4 }}>
                {b.label}
              </label>
              <p style={{ margin: "0 0 8px", color: "var(--muted)", fontSize: 12 }}>{b.hint}</p>
              <textarea
                className="input"
                rows={Math.min(12, Math.max(4, Math.round(b.palavras_alvo[1] / 40)))}
                value={doc.conteudo[b.id] || ""}
                onChange={(e) => {
                  const c = { ...doc.conteudo, [b.id]: e.target.value };
                  setDoc({ ...doc, conteudo: c });
                  scheduleSave();
                }}
                disabled={finalizado}
              />
            </Card>
          ))}
        </div>

        <div style={{ display: "flex", gap: 12, marginTop: 20, justifyContent: "flex-end" }}>
          {finalizado && doc.anexo_pdf_id && (
            <a className="btn" href={`${API_BASE}/anexos/${doc.anexo_pdf_id}/arquivo`} target="_blank" rel="noreferrer">
              <Download size={16} /> Baixar PDF
            </a>
          )}
          {!finalizado && (
            <>
              <Button variant={temCertValido ? "primary" : undefined} onClick={() => setIcpOpen(true)} disabled={!!busy}>
                <ShieldCheck size={16} /> Assinar com ICP-Brasil
              </Button>
              <Button variant={temCertValido ? undefined : "primary"} onClick={() => setConfirmAssinar(true)} disabled={!!busy}>
                <FileCheck2 size={16} /> Assinar (simples)
              </Button>
            </>
          )}
        </div>

        {verif && verif.assinado && (
          <Card style={{ marginTop: 12, display: "flex", gap: 10, alignItems: "flex-start" }}>
            <BadgeCheck size={20} color={verif.valido && verif.intacto ? "var(--pos-fg)" : "var(--warn-fg)"} style={{ flexShrink: 0, marginTop: 2 }} />
            <div>
              <div style={{ fontWeight: 500 }}>
                Assinatura ICP-Brasil (PAdES) — {verif.intacto && verif.valido ? "íntegra e válida" : "verificar"}
              </div>
              <div style={{ color: "var(--muted)", fontSize: 12, marginTop: 2 }}>
                Titular: {verif.titular || doc.cert_titular || "—"} · algoritmo {verif.algoritmo || "—"}
              </div>
              {verif.nota && (
                <div style={{ color: "var(--muted)", fontSize: 11, marginTop: 4 }}>{verif.nota}</div>
              )}
            </div>
          </Card>
        )}

        {finalizado && doc.hash_assinatura && (
          <p style={{ marginTop: 12, color: "var(--muted)", fontSize: 11, fontFamily: "monospace" }}>
            SHA-256: {doc.hash_assinatura}
          </p>
        )}
        <p style={{ marginTop: 8, color: "var(--muted)", fontSize: 11 }}>{doc.aviso}</p>
      </main>

      <Drawer open={icpOpen} title="Assinar com ICP-Brasil" onClose={() => { setIcpOpen(false); setSenhaIcp(""); }}>
        <p style={{ color: "var(--muted)", fontSize: 13, margin: 0 }}>
          Assinatura digital qualificada (PAdES/A1) com o seu certificado. A senha é usada
          apenas neste ato e <b>não é armazenada</b>. Ao assinar, o documento fica <b>imutável</b>.
        </p>
        <p style={{ color: "var(--muted)", fontSize: 12, margin: 0 }}>
          Requer um certificado A1 cadastrado em <Link className="link" href="/conta/2fa">Conta</Link>.
        </p>
        <form onSubmit={(e) => { e.preventDefault(); assinarIcp(); }} style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <Field label="Senha do certificado">
            <input className="input" type="password" autoFocus value={senhaIcp}
              onChange={(e) => setSenhaIcp(e.target.value)} placeholder="••••••••" />
          </Field>
          <Button variant="primary" disabled={!!busy || !senhaIcp}>
            <ShieldCheck size={16} /> {busy || "Assinar documento"}
          </Button>
        </form>
      </Drawer>

      <ConfirmDialog
        open={confirmAssinar}
        title="Assinar documento"
        description="Após assinar, o documento fica imutável e o PDF é anexado ao prontuário do paciente."
        confirmLabel="Assinar"
        cancelLabel="Continuar revisando"
        confirmVariant="primary"
        busy={busy === "Assinando…"}
        busyLabel="Assinando…"
        onConfirm={assinar}
        onCancel={() => setConfirmAssinar(false)}
      />
    </>
  );
}
