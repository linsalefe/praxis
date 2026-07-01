"use client";

import { useEffect, useRef, useState, use } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import { Compass, Copy, Quote, Trash2 } from "lucide-react";
import { api, ApiError, getToken } from "@/lib/api";
import { Topbar } from "@/components/Topbar";

type Citacao = {
  n: number; titulo: string; autor: string;
  is_terceiro: boolean; capitulo: string | null;
  pagina_inicio: number | null; pagina_fim: number | null;
  snippet: string; similaridade: number;
};

type Estudo = {
  id: string; autor_id: string; origem: string;
  paciente_id: string | null; caso_hash: string | null;
  texto_analise: string; citacoes: Citacao[];
  provider: string | null; meta: Record<string, unknown>;
  criado_em: string; atualizado_em: string;
  disclaimer: string;
};

export default function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const [e, setE] = useState<Estudo | null>(null);
  const [drawer, setDrawer] = useState<Citacao | null>(null);
  const [dirty, setDirty] = useState(false);
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!getToken()) return void router.replace("/login");
    (async () => {
      try { setE(await api<Estudo>(`/supervisao/estudos/${id}`)); }
      catch (err) {
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
    if (!e) return;
    try {
      const r = await api<Estudo>(`/supervisao/estudos/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ texto_analise: e.texto_analise }),
      });
      setE(r);
      setDirty(false);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Falha ao salvar");
    }
  }

  async function remover() {
    if (!confirm("Remover este estudo?")) return;
    try {
      await api(`/supervisao/estudos/${id}`, { method: "DELETE" });
      toast.success("Removido.");
      router.push("/supervisao");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Falha");
    }
  }

  async function copiar() {
    if (!e) return;
    try {
      await navigator.clipboard.writeText(e.texto_analise);
      toast.success("Copiado.");
    } catch { toast.error("Falha ao copiar"); }
  }

  if (!e) return (<><Topbar /><main className="container-praxis"><p style={{ color: "var(--muted)" }}>Carregando…</p></main></>);

  return (
    <>
      <Topbar />
      <main className="container-praxis" style={{ maxWidth: 900 }}>
        <p style={{ margin: 0 }}>
          <Link className="link" href="/supervisao">← Supervisão</Link>
        </p>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: 8 }}>
          <h1 style={{ fontSize: 22, margin: 0, display: "flex", alignItems: "center", gap: 8 }}>
            <Compass size={20} color="var(--brand-2)" /> Estudo de caso
          </h1>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span className="badge">{e.origem === "paciente" ? "prontuário" : "avulso"}</span>
            {dirty && <span className="badge">salvando…</span>}
          </div>
        </div>
        <p style={{ color: "var(--muted)", fontSize: 12, marginTop: 4 }}>
          Gerado por <span className="badge">{e.provider}</span> ·
          {" "}{String((e.meta.abordagens_comparadas as string[] | undefined)?.length || 0)} abordagens ·
          {" "}{String(e.meta.n_chunks_acervo || 0)} trechos do acervo
        </p>

        <textarea
          className="input"
          rows={22}
          value={e.texto_analise}
          onChange={(ev) => { setE({ ...e, texto_analise: ev.target.value }); scheduleSave(); }}
          style={{ fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace", fontSize: 12.5, lineHeight: 1.5 }}
        />

        {e.citacoes.length > 0 && (
          <div style={{ marginTop: 12 }}>
            <div style={{ fontSize: 12, color: "var(--muted)", marginBottom: 4 }}>
              <Quote size={12} style={{ display: "inline", verticalAlign: "middle" }} /> Fontes usadas
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              {e.citacoes.map((c) => (
                <button key={c.n} className="badge" style={{ cursor: "pointer" }} onClick={() => setDrawer(c)}>
                  T{c.n} · {c.titulo.slice(0, 42)}
                  {c.is_terceiro && <span style={{ color: "var(--brand-2)", marginLeft: 4 }}>[3º]</span>}
                </button>
              ))}
            </div>
          </div>
        )}

        <div style={{ display: "flex", gap: 8, marginTop: 16, justifyContent: "space-between" }}>
          <button className="btn btn-danger" onClick={remover}>
            <Trash2 size={14} /> Remover estudo
          </button>
          <button className="btn btn-primary" onClick={copiar}>
            <Copy size={14} /> Copiar texto
          </button>
        </div>

        <p style={{ marginTop: 12, color: "var(--muted)", fontSize: 11 }}>
          {e.disclaimer}
        </p>

        {drawer && (
          <div
            role="dialog" aria-modal="true"
            style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 40 }}
            onClick={() => setDrawer(null)}
          >
            <div className="card" style={{ maxWidth: 640, width: "92%" }} onClick={(ev) => ev.stopPropagation()}>
              <h3 style={{ marginTop: 0 }}>{drawer.titulo}</h3>
              <p style={{ color: "var(--muted)", margin: "4px 0" }}>{drawer.autor}</p>
              <p style={{ margin: "4px 0" }}>
                <span className="badge">cap. {drawer.capitulo || "n/d"}</span>{" "}
                <span className="badge">
                  {drawer.pagina_inicio ? `pp. ${drawer.pagina_inicio}${drawer.pagina_fim && drawer.pagina_fim !== drawer.pagina_inicio ? `-${drawer.pagina_fim}` : ""}` : "p. n/d"}
                </span>{" "}
                <span className="badge">sim {(drawer.similaridade * 100).toFixed(0)}%</span>
                {drawer.is_terceiro && <span className="badge" style={{ color: "var(--brand-2)" }}>terceiro — paráfrase</span>}
              </p>
              <hr className="divider" />
              <p style={{ whiteSpace: "pre-wrap" }}>{drawer.snippet}</p>
              <div style={{ textAlign: "right", marginTop: 12 }}>
                <button className="btn" onClick={() => setDrawer(null)}>Fechar</button>
              </div>
            </div>
          </div>
        )}
      </main>
    </>
  );
}
