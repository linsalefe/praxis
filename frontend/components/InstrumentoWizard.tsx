"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import { ChevronLeft, ChevronRight, Download, FileCheck2 } from "lucide-react";
import { api, ApiError, getToken } from "@/lib/api";
import { Topbar } from "@/components/Topbar";
import { PresenceMark } from "@/components/ui/PresenceMark";
import { InstrumentoFaixa, FaixaSeveridade, type FaixaDef } from "@/components/ui/InstrumentoFaixa";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8040";

type Pergunta = {
  id: string; tipo: string; label: string;
  opcoes?: string[]; obrigatorio?: boolean;
};
type Secao = { id: string; titulo: string; descricao?: string; perguntas: Pergunta[] };
type OpcaoLikert = { valor: number; rotulo: string };
type ItemLikert = { id: string; texto: string; invertido?: boolean; subescala?: string; flag?: string };
type SubescalaDef = { id: string; rotulo: string; itens: string[]; faixas: FaixaDef[]; multiplicador?: number };
type Definicao = {
  secoes?: Secao[];
  kind?: string;
  instrucoes?: string;
  opcoes?: OpcaoLikert[];
  itens?: ItemLikert[];
  faixas?: FaixaDef[];
  subescalas?: SubescalaDef[];
};
type Instrumento = {
  id: string; tipo: string; versao: string; titulo: string;
  descricao: string | null; fonte: string | null; definicao?: Definicao;
};
type Subescore = {
  id: string; rotulo: string; escore: number; itens_respondidos: number;
  total_itens: number; completo: boolean; faixa_rotulo: string | null; severidade: string | null;
};
type Pontuacao = {
  tipo: "unico" | "subescalas";
  escore: number | null; escore_bruto: number | null; transformado: number | null;
  faixa_rotulo: string | null; severidade: string | null;
  itens_respondidos: number; total_itens: number; completo: boolean;
  subescores: Subescore[];
};
type Resposta = {
  id: string; paciente_id: string; instrumento_tipo: string;
  instrumento_versao: string; status: "em_andamento" | "finalizado";
  respostas: Record<string, Record<string, unknown>>;
  saida_texto: string | null; saida_gerada_em: string | null;
  saida_provider: string | null; finalizado_em: string | null;
  anexo_id: string | null;
  pontuacao: Pontuacao | null;
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

  const isLikert = instr?.definicao?.kind === "likert_sum";
  const secoes = isLikert ? [] : (instr?.definicao?.secoes ?? []);
  // likert: 1 passo de itens + 1 de saída. qualitativo: 1 passo por seção + saída.
  const passosItens = isLikert ? 1 : secoes.length;
  const total = passosItens + 1;
  const isSaidaStep = step >= passosItens;

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

  // likert_sum: respostas ficam numa única seção "itens" { itemId: valor }
  function updItem(itemId: string, valor: number) {
    if (!resp) return;
    setResp({
      ...resp,
      respostas: { ...resp.respostas, itens: { ...(resp.respostas.itens || {}), [itemId]: valor } },
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

        {!isSaidaStep && !isLikert && (
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

        {!isSaidaStep && isLikert && instr.definicao && (
          <>
            <div className="card" style={{ marginTop: 12 }}>
              {instr.definicao.instrucoes && (
                <p style={{ color: "var(--muted)", fontSize: 13, marginTop: 0 }}>{instr.definicao.instrucoes}</p>
              )}
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {(instr.definicao.itens || []).map((it, idx) => (
                  <ItemLikertCampo
                    key={it.id}
                    idx={idx + 1}
                    item={it}
                    opcoes={instr.definicao!.opcoes || []}
                    valor={(resp.respostas.itens || {})[it.id] as number | undefined}
                    onChange={(v) => updItem(it.id, v)}
                    disabled={finalizado}
                  />
                ))}
              </div>
            </div>
            <div className="card" style={{ marginTop: 12 }}>
              <h2 style={{ fontSize: 15, marginTop: 0 }}>Escore (calculado)</h2>
              <p style={{ color: "var(--muted)", fontSize: 12, margin: "0 0 12px" }}>
                O escore e a faixa são calculados pelo servidor — factuais. A interpretação clínica é do profissional.
              </p>
              <PainelFaixa definicao={instr.definicao} pontuacao={resp.pontuacao} />
            </div>
          </>
        )}

        {isSaidaStep && (
          <div className="card" style={{ marginTop: 12 }}>
            <h2 style={{ fontSize: 15, marginTop: 0 }}>Saída — revise e finalize</h2>
            {isLikert && instr.definicao && (
              <div style={{ marginBottom: 12, paddingBottom: 12, borderBottom: "1px solid var(--border)" }}>
                <PainelFaixa definicao={instr.definicao} pontuacao={resp.pontuacao} />
                <p style={{ color: "var(--warm-500)", fontSize: 11, margin: "8px 0 0", fontFamily: "var(--font-mono)" }}>
                  Escore factual acima. O texto abaixo é interpretação (rascunho editável) — separado do número.
                </p>
              </div>
            )}
            <p style={{ color: "var(--muted)", fontSize: 13, margin: "0 0 12px" }}>
              Gere um rascunho com IA e edite livremente. O PDF fica anexado ao prontuário do paciente.
              Enquanto não finalizar, permanece rascunho editável.
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
          <button className="btn" onClick={() => setStep((s) => Math.min(passosItens, s + 1))} disabled={step >= passosItens}>
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

function PainelFaixa({ definicao, pontuacao }: { definicao: Definicao; pontuacao: Pontuacao | null }) {
  if (!pontuacao) return <p style={{ color: "var(--muted)", fontSize: 13 }}>Responda os itens para ver o escore.</p>;

  if (pontuacao.tipo === "subescalas") {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        {(definicao.subescalas || []).map((sub) => {
          const s = pontuacao.subescores.find((x) => x.id === sub.id);
          if (!s) return null;
          return (
            <FaixaSeveridade
              key={sub.id}
              rotulo={sub.rotulo}
              escore={s.escore}
              faixas={sub.faixas}
              faixaRotulo={s.faixa_rotulo}
              severidade={s.severidade}
              completo={s.completo}
            />
          );
        })}
      </div>
    );
  }

  return (
    <FaixaSeveridade
      rotulo="Escore total"
      escore={pontuacao.escore}
      escoreBruto={pontuacao.escore_bruto}
      faixas={definicao.faixas || []}
      faixaRotulo={pontuacao.faixa_rotulo}
      severidade={pontuacao.severidade}
      completo={pontuacao.completo}
    />
  );
}

function ItemLikertCampo({
  idx, item, opcoes, valor, onChange, disabled,
}: {
  idx: number;
  item: ItemLikert;
  opcoes: OpcaoLikert[];
  valor: number | undefined;
  onChange: (v: number) => void;
  disabled?: boolean;
}) {
  return (
    <div style={{ padding: "10px 0", borderBottom: "1px solid var(--border)" }}>
      <div style={{ fontSize: 13, color: "var(--text)", marginBottom: 8 }}>
        <span style={{ fontFamily: "var(--font-mono)", color: "var(--warm-500)" }}>{idx}.</span>{" "}
        {item.texto}
        {item.flag === "risco" && (
          <span className="badge badge-risk" style={{ marginLeft: 6, fontSize: 10 }}>atenção</span>
        )}
      </div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
        {opcoes.map((o) => {
          const on = valor === o.valor;
          return (
            <label
              key={o.valor}
              className={`badge ${on ? "badge-info" : ""}`}
              style={{ cursor: disabled ? "default" : "pointer", opacity: disabled && !on ? 0.5 : 1 }}
            >
              <input
                type="radio"
                name={`item-${item.id}`}
                checked={on}
                disabled={disabled}
                onChange={() => onChange(o.valor)}
                style={{ marginRight: 4 }}
              />
              {o.rotulo}
            </label>
          );
        })}
      </div>
    </div>
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
