"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import { ChevronLeft, ChevronRight, Download, FileCheck2 } from "lucide-react";
import { api, ApiError, getToken } from "@/lib/api";
import { Topbar } from "@/components/Topbar";
import { PresenceMark } from "@/components/ui/PresenceMark";
import { InstrumentoFaixa } from "@/components/ui/InstrumentoFaixa";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8040";

type Pergunta = {
  id: string; tipo: string; label: string;
  opcoes?: string[]; obrigatorio?: boolean;
};
type Secao = { id: string; titulo: string; descricao?: string; perguntas: Pergunta[] };
type Definicao = { secoes: Secao[] };
type Instrumento = {
  id: string; tipo: string; versao: string; titulo: string;
  descricao: string | null; fonte: string | null; definicao?: Definicao;
};
type Resposta = {
  id: string; paciente_id: string; instrumento_tipo: string;
  instrumento_versao: string; status: "em_andamento" | "finalizado";
  respostas: Record<string, Record<string, unknown>>;
  saida_texto: string | null; saida_gerada_em: string | null;
  saida_provider: string | null; finalizado_em: string | null;
  anexo_id: string | null;
};

export function InstrumentoWizard({ respostaId }: { respostaId: string }) {
  const router = useRouter();
  const [instr, setInstr] = useState<Instrumento | null>(null);
  const [resp, setResp] = useState<Resposta | null>(null);
  const [step, setStep] = useState(0);
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!getToken()) return void router.replace("/login");
    (async () => {
      try {
        const r = await api<Resposta>(`/respostas-instrumento/${respostaId}`);
        setResp(r);
        const i = await api<Instrumento>(`/instrumentos/${r.instrumento_tipo}`);
        setInstr(i);
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) router.replace("/login");
        else toast.error(err instanceof ApiError ? err.message : "Erro");
      }
    })();
  }, [respostaId, router]);

  const secoes = instr?.definicao?.secoes ?? [];
  const total = secoes.length + 1; // + tela final
  const isSaidaStep = step >= secoes.length;

  const scheduleSave = () => {
    setDirty(true);
    if (saveTimer.current) clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(salvar, 800);
  };

  async function salvar() {
    if (!resp) return;
    try {
      const r = await api<Resposta>(`/respostas-instrumento/${resp.id}`, {
        method: "PATCH",
        body: JSON.stringify({ respostas: resp.respostas, saida_texto: resp.saida_texto }),
      });
      setResp(r);
      setDirty(false);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Falha ao salvar");
    }
  }

  async function gerar() {
    if (!resp) return;
    setBusy("Gerando saída…");
    try {
      const r = await api<{ resposta_id: string; saida_texto: string; provider: string }>(
        `/respostas-instrumento/${resp.id}/gerar-saida`,
        { method: "POST" },
      );
      const refreshed = await api<Resposta>(`/respostas-instrumento/${resp.id}`);
      setResp(refreshed);
      toast.success(`Rascunho gerado (${r.provider}).`);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Falha ao gerar");
    } finally {
      setBusy(null);
    }
  }

  async function finalizar() {
    if (!resp) return;
    if (!resp.saida_texto?.trim()) {
      toast.error("Gere ou escreva a saída antes de finalizar.");
      return;
    }
    if (dirty) await salvar();
    setBusy("Gerando PDF…");
    try {
      const a = await api<{ id: string }>(`/respostas-instrumento/${resp.id}/finalizar`, { method: "POST" });
      toast.success("Instrumento finalizado e anexado ao prontuário.");
      router.push(`/pacientes/${resp.paciente_id}?tab=anexos&novo=${a.id}`);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Falha ao finalizar");
    } finally {
      setBusy(null);
    }
  }

  function upd(secId: string, pergId: string, valor: unknown) {
    if (!resp) return;
    setResp({
      ...resp,
      respostas: {
        ...resp.respostas,
        [secId]: { ...(resp.respostas[secId] || {}), [pergId]: valor },
      },
    });
    scheduleSave();
  }

  if (!instr || !resp)
    return (
      <>
        <Topbar />
        <main className="container-praxis"><p style={{ color: "var(--muted)" }}>Carregando…</p></main>
      </>
    );

  const finalizado = resp.status === "finalizado";

  return (
    <>
      <Topbar />
      <main className="container-praxis" style={{ maxWidth: 900 }}>
        <p style={{ margin: 0 }}>
          <Link className="link" href={`/pacientes/${resp.paciente_id}`}>← Paciente</Link>
        </p>
        <div className="card" style={{ marginTop: 8 }}>
          <InstrumentoFaixa
            titulo={instr.titulo}
            versao={instr.versao}
            status={resp.status}
            atual={Math.min(step + 1, total)}
            total={total}
          />
          {dirty && (
            <div style={{ marginTop: 8, fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--warm-500)" }}>
              salvando…
            </div>
          )}
          {instr.descricao && (
            <p style={{ color: "var(--muted)", fontSize: 13, margin: "10px 0 0" }}>{instr.descricao}</p>
          )}
        </div>

        {!isSaidaStep && (
          <div className="card" style={{ marginTop: 12 }}>
            <h2 style={{ fontSize: 15, marginTop: 0 }}>{secoes[step].titulo}</h2>
            {secoes[step].descricao && (
              <p style={{ color: "var(--muted)", fontSize: 13, marginTop: 0 }}>{secoes[step].descricao}</p>
            )}
            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              {secoes[step].perguntas.map((p) => (
                <CampoResposta
                  key={p.id}
                  pergunta={p}
                  valor={(resp.respostas[secoes[step].id] || {})[p.id]}
                  onChange={(v) => upd(secoes[step].id, p.id, v)}
                  disabled={finalizado}
                />
              ))}
            </div>
          </div>
        )}

        {isSaidaStep && (
          <div className="card" style={{ marginTop: 12 }}>
            <h2 style={{ fontSize: 15, marginTop: 0 }}>Saída — revise e finalize</h2>
            <p style={{ color: "var(--muted)", fontSize: 13, margin: "0 0 12px" }}>
              Gere um rascunho com IA (baseado no acervo, para Maastricht) e edite livremente.
              O PDF fica anexado ao prontuário do paciente. Enquanto não finalizar, permanece rascunho editável.
            </p>
            <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
              <button className="btn" onClick={gerar} disabled={!!busy || finalizado}>
                <PresenceMark size={16} /> {busy || "Gerar rascunho"}
              </button>
              {resp.saida_provider && (
                <span className="badge">{resp.saida_provider}</span>
              )}
            </div>
            <textarea
              className="input"
              rows={18}
              value={resp.saida_texto || ""}
              onChange={(e) => { setResp({ ...resp, saida_texto: e.target.value }); scheduleSave(); }}
              placeholder="A saída aparecerá aqui. Você pode escrever direto se preferir."
              disabled={finalizado}
            />
            <div style={{ marginTop: 12, display: "flex", gap: 8, justifyContent: "flex-end" }}>
              {finalizado && resp.anexo_id && (
                <a className="btn" href={`${API_BASE}/anexos/${resp.anexo_id}/arquivo`} target="_blank" rel="noreferrer">
                  <Download size={16} /> Baixar PDF anexado
                </a>
              )}
              {!finalizado && (
                <button className="btn btn-primary" onClick={finalizar} disabled={!!busy}>
                  <FileCheck2 size={16} /> {busy || "Finalizar e anexar PDF"}
                </button>
              )}
            </div>
          </div>
        )}

        <div style={{ display: "flex", justifyContent: "space-between", marginTop: 16 }}>
          <button className="btn" onClick={() => setStep((s) => Math.max(0, s - 1))} disabled={step === 0}>
            <ChevronLeft size={16} /> Anterior
          </button>
          <button className="btn" onClick={() => setStep((s) => Math.min(secoes.length, s + 1))} disabled={step >= secoes.length}>
            Próximo <ChevronRight size={16} />
          </button>
        </div>

        <p style={{ marginTop: 16, color: "var(--muted)", fontSize: 11 }}>
          {instr.fonte}
        </p>
      </main>
    </>
  );
}

function CampoResposta({
  pergunta, valor, onChange, disabled,
}: {
  pergunta: Pergunta;
  valor: unknown;
  onChange: (v: unknown) => void;
  disabled?: boolean;
}) {
  const v = valor;
  const label = (
    <label className="label" style={{ fontSize: 13, color: "var(--text)" }}>
      {pergunta.label}{pergunta.obrigatorio && " *"}
    </label>
  );
  switch (pergunta.tipo) {
    case "textarea":
      return (
        <div>
          {label}
          <textarea className="input" rows={3} value={(v as string) || ""}
            onChange={(e) => onChange(e.target.value)} disabled={disabled} />
        </div>
      );
    case "integer":
      return (
        <div>
          {label}
          <input className="input" type="number" inputMode="numeric"
            value={(v as number | null) ?? ""}
            onChange={(e) => onChange(e.target.value === "" ? null : Number(e.target.value))}
            disabled={disabled} />
        </div>
      );
    case "date":
      return (
        <div>
          {label}
          <input className="input" type="date" value={(v as string) || ""}
            onChange={(e) => onChange(e.target.value)} disabled={disabled} />
        </div>
      );
    case "select":
      return (
        <div>
          {label}
          <select className="input" value={(v as string) || ""}
            onChange={(e) => onChange(e.target.value)} disabled={disabled}>
            <option value="">—</option>
            {(pergunta.opcoes || []).map((o) => <option key={o} value={o}>{o}</option>)}
          </select>
        </div>
      );
    case "multiselect":
      return (
        <div>
          {label}
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {(pergunta.opcoes || []).map((o) => {
              const arr = (v as string[]) || [];
              const on = arr.includes(o);
              return (
                <label key={o} className="badge" style={{ cursor: "pointer", opacity: disabled ? 0.6 : 1 }}>
                  <input type="checkbox" checked={on} disabled={disabled}
                    onChange={() => onChange(on ? arr.filter((x) => x !== o) : [...arr, o])} />
                  {" "}{o}
                </label>
              );
            })}
          </div>
        </div>
      );
    case "boolean":
      return (
        <div>
          <label className="badge" style={{ cursor: "pointer" }}>
            <input type="checkbox" checked={!!v} disabled={disabled}
              onChange={(e) => onChange(e.target.checked)} /> {pergunta.label}
          </label>
        </div>
      );
    case "escala":
      return (
        <div>
          {label}
          <input className="input" type="range" min={0} max={10}
            value={(v as number) ?? 5}
            onChange={(e) => onChange(Number(e.target.value))} disabled={disabled} />
          <div style={{ textAlign: "right", color: "var(--muted)", fontSize: 12 }}>
            valor: {(v as number) ?? 5}/10
          </div>
        </div>
      );
    default:
      return (
        <div>
          {label}
          <input className="input" value={(v as string) || ""}
            onChange={(e) => onChange(e.target.value)} disabled={disabled} />
        </div>
      );
  }
}
