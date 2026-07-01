"use client";

import { useEffect, useRef, useState, use } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import { Download, FileCheck2, FileSignature, RefreshCcw } from "lucide-react";
import { api, ApiError, getToken } from "@/lib/api";
import { Topbar } from "@/components/Topbar";

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
  criado_em: string; atualizado_em: string;
  aviso: string;
};

export default function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const [doc, setDoc] = useState<Doc | null>(null);
  const [tpl, setTpl] = useState<Template | null>(null);
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!getToken()) return void router.replace("/login");
    (async () => {
      try {
        const d = await api<Doc>(`/documentos/${id}`);
        setDoc(d);
        const templates = await api<Template[]>("/documentos/templates");
        setTpl(templates.find((t) => t.tipo === d.tipo) || null);
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
      toast.success("Documento assinado e anexado ao prontuário.");
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

  return (
    <>
      <Topbar />
      <main className="container-praxis" style={{ maxWidth: 880 }}>
        <p style={{ margin: 0 }}>
          <Link className="link" href={`/pacientes/${doc.paciente_id}`}>← Paciente</Link>
        </p>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: 8 }}>
          <h1 style={{ fontSize: 22, margin: 0, display: "flex", alignItems: "center", gap: 8 }}>
            <FileSignature size={20} color="var(--brand-2)" /> {tpl.titulo}
          </h1>
          <span className="badge">
            {finalizado ? "assinado" : "rascunho"}{dirty ? " · salvando…" : ""}
          </span>
        </div>
        <p style={{ color: "var(--muted)", fontSize: 13, margin: "4px 0 12px" }}>{tpl.descricao}</p>

        <div className="card">
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
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 12, marginTop: 12 }}>
          {tpl.blocos.map((b) => (
            <div key={b.id} className="card">
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
            </div>
          ))}
        </div>

        <div style={{ display: "flex", gap: 12, marginTop: 20, justifyContent: "flex-end" }}>
          {finalizado && doc.anexo_pdf_id && (
            <a className="btn" href={`${API_BASE}/anexos/${doc.anexo_pdf_id}/arquivo`} target="_blank" rel="noreferrer">
              <Download size={16} /> Baixar PDF
            </a>
          )}
          {!finalizado && (
            <button className="btn btn-primary" onClick={assinar} disabled={!!busy}>
              <FileCheck2 size={16} /> {busy || "Assinar e anexar PDF"}
            </button>
          )}
        </div>

        {finalizado && doc.hash_assinatura && (
          <p style={{ marginTop: 12, color: "var(--muted)", fontSize: 11, fontFamily: "monospace" }}>
            SHA-256: {doc.hash_assinatura}
          </p>
        )}
        <p style={{ marginTop: 8, color: "var(--muted)", fontSize: 11 }}>{doc.aviso}</p>
      </main>
    </>
  );
}
