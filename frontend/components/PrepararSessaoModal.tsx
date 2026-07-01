"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { ClipboardCheck, Copy, Link2, Quote, X, Wand2 } from "lucide-react";
import { api, ApiError } from "@/lib/api";

type Citacao = {
  n: number; titulo: string; autor: string; is_terceiro: boolean;
  capitulo: string | null; pagina_inicio: number | null; pagina_fim: number | null;
  snippet: string; similaridade: number;
};

type Roteiro = {
  id: string; paciente_id: string; sessao_id: string | null; autor_id: string;
  texto: string; citacoes: Citacao[]; provider: string | null;
  meta: Record<string, unknown>; criado_em: string; atualizado_em: string;
  disclaimer: string;
};

type Sessao = {
  id: string; data: string; modalidade: string; status: string;
};

export function PrepararSessaoModal({
  pacienteId, onClose,
}: {
  pacienteId: string;
  onClose: () => void;
}) {
  const [roteiro, setRoteiro] = useState<Roteiro | null>(null);
  const [sessoes, setSessoes] = useState<Sessao[]>([]);
  const [sessIdVincular, setSessIdVincular] = useState("");
  const [busy, setBusy] = useState<string | null>("Preparando…");

  useEffect(() => {
    (async () => {
      try {
        const [r, sess] = await Promise.all([
          api<Roteiro>("/sessao/preparar", {
            method: "POST",
            body: JSON.stringify({ paciente_id: pacienteId }),
          }),
          api<Sessao[]>(`/sessoes/paciente/${pacienteId}`),
        ]);
        setRoteiro(r);
        setSessoes(sess);
        if (r.sessao_id) setSessIdVincular(r.sessao_id);
      } catch (err) {
        toast.error(err instanceof ApiError ? err.message : "Falha ao preparar");
        setBusy(null);
      } finally {
        setBusy(null);
      }
    })();
  }, [pacienteId]);

  async function copiar() {
    if (!roteiro) return;
    try {
      await navigator.clipboard.writeText(roteiro.texto);
      toast.success("Roteiro copiado.");
    } catch {
      toast.error("Falha ao copiar");
    }
  }

  async function vincular() {
    if (!roteiro) return;
    setBusy("Salvando…");
    try {
      const r = await api<Roteiro>(`/roteiros/${roteiro.id}`, {
        method: "PATCH",
        body: JSON.stringify({ sessao_id: sessIdVincular || "" }),
      });
      setRoteiro(r);
      toast.success(r.sessao_id ? "Roteiro vinculado à sessão." : "Vínculo removido.");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Falha");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      style={{
        position: "fixed", inset: 0, background: "rgba(0,0,0,0.55)",
        display: "flex", alignItems: "center", justifyContent: "center", zIndex: 50,
      }}
      onClick={busy ? undefined : onClose}
    >
      <div
        className="card"
        style={{ width: "94%", maxWidth: 820, maxHeight: "88vh", overflow: "hidden", display: "flex", flexDirection: "column" }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <h3 style={{ margin: 0, display: "flex", alignItems: "center", gap: 8 }}>
            <ClipboardCheck size={18} color="var(--brand-2)" /> Preparação de sessão
          </h3>
          <button className="btn" onClick={onClose} disabled={!!busy}><X size={14} /></button>
        </div>

        {busy && (
          <p style={{ color: "var(--muted)", fontSize: 13, marginTop: 12 }}>
            {busy}
          </p>
        )}

        {roteiro && (
          <>
            <p style={{ color: "var(--muted)", fontSize: 12, margin: "8px 0 4px" }}>
              Gerado por <span className="badge">{roteiro.provider}</span>{" "}
              usando {String(roteiro.meta.n_evolucoes_usadas || 0)} evolução(ões), {String(roteiro.meta.n_instrumentos_usados || 0)} instrumento(s) e {String(roteiro.meta.n_chunks_acervo || 0)} trecho(s) do acervo.
              Nome e dados pessoais do paciente não foram enviados à IA.
            </p>

            <div
              style={{
                background: "var(--surface-2)",
                border: "1px solid var(--border)",
                borderRadius: 8, padding: 16, marginTop: 8,
                whiteSpace: "pre-wrap", fontSize: 13, lineHeight: 1.5,
                overflowY: "auto", flex: 1,
              }}
            >
              {roteiro.texto}
            </div>

            {roteiro.citacoes.length > 0 && (
              <div style={{ marginTop: 10 }}>
                <div style={{ fontSize: 12, color: "var(--muted)", marginBottom: 4 }}>
                  <Quote size={12} style={{ display: "inline", verticalAlign: "middle" }} /> Fontes usadas
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                  {roteiro.citacoes.map((c) => (
                    <span key={c.n} className="badge" title={c.snippet}>
                      T{c.n} · {c.titulo.slice(0, 40)}
                      {c.is_terceiro && <span style={{ color: "var(--brand-2)", marginLeft: 4 }}>[3º]</span>}
                    </span>
                  ))}
                </div>
              </div>
            )}

            <div
              style={{
                marginTop: 12, display: "flex", gap: 8, flexWrap: "wrap",
                alignItems: "center", justifyContent: "space-between",
              }}
            >
              <div style={{ display: "flex", gap: 6, alignItems: "center", flex: 1 }}>
                <Link2 size={14} color="var(--muted)" />
                <select
                  className="input"
                  style={{ width: "auto", maxWidth: 320 }}
                  value={sessIdVincular}
                  onChange={(e) => setSessIdVincular(e.target.value)}
                  disabled={!!busy}
                >
                  <option value="">— não vincular —</option>
                  {sessoes.map((s) => (
                    <option key={s.id} value={s.id}>
                      {new Date(s.data).toLocaleString("pt-BR")} · {s.modalidade} · {s.status}
                    </option>
                  ))}
                </select>
                <button className="btn" onClick={vincular} disabled={!!busy}>
                  Salvar vínculo
                </button>
              </div>
              <button className="btn btn-primary" onClick={copiar} disabled={!!busy}>
                <Copy size={14} /> Copiar
              </button>
            </div>

            <p style={{ marginTop: 10, color: "var(--muted)", fontSize: 11 }}>
              {roteiro.disclaimer}
            </p>
          </>
        )}
      </div>
    </div>
  );
}
