"use client";

import { BookOpen, ClipboardCheck, Quote } from "lucide-react";
import { PresenceMark } from "@/components/ui/PresenceMark";
import { CopiarBtn } from "@/components/ui/CopiarBtn";
import { Button } from "@/components/ui/Button";

/**
 * SofiaOrientacao — a assinatura da Sofia.
 * Moldura com lombada (âmbar→petróleo), cabeçalho com PresenceMark, corpo da
 * resposta, citações reais (título/autor + similaridade; is_terceiro → paráfrase
 * obrigatória), disclaimer e callout de "sem respaldo no acervo".
 * O estado de carregamento é a PresenceMark respirando — nunca um spinner.
 */

export interface SofiaCitacaoBase {
  n: number;
  slug: string;
  titulo: string;
  autor: string;
  is_terceiro: boolean;
  capitulo: string | null;
  pagina_inicio: number | null;
  pagina_fim: number | null;
  similaridade: number;
}

export interface SofiaRespostaBase<C extends SofiaCitacaoBase = SofiaCitacaoBase> {
  resposta: string;
  citacoes: C[];
  sem_respaldo: boolean;
  disclaimer: string;
  modelo: string;
}

export function SofiaOrientacao<C extends SofiaCitacaoBase>({
  pergunta,
  resposta,
  loading,
  streaming,
  erro,
  onCitacao,
  onUsarNaPreparacao,
}: {
  pergunta: string;
  resposta: SofiaRespostaBase<C> | null;
  loading?: boolean;
  streaming?: boolean;
  erro?: string;
  onCitacao?: (c: C) => void;
  onUsarNaPreparacao?: () => void;
}) {
  return (
    <div style={{ marginBottom: 24 }}>
      {/* Pergunta do profissional */}
      <div style={{ marginBottom: 10 }}>
        <div style={{ color: "var(--muted)", fontSize: 12, marginBottom: 2 }}>Você</div>
        <div>{pergunta}</div>
      </div>

      {/* Moldura da orientação */}
      <div
        style={{
          position: "relative",
          background: "var(--surface)",
          border: "1px solid var(--teal-200)",
          borderRadius: "var(--radius-lg)",
          boxShadow: "var(--shadow-md)",
          padding: "16px 18px 16px 22px",
          overflow: "hidden",
        }}
      >
        {/* Lombada */}
        <span
          aria-hidden
          style={{
            position: "absolute",
            left: 0,
            top: 0,
            bottom: 0,
            width: 5,
            background: "linear-gradient(var(--accent), var(--teal-500))",
          }}
        />

        {/* Cabeçalho */}
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
          <PresenceMark size={30} />
          <div style={{ lineHeight: 1.2 }}>
            <div style={{ fontFamily: "var(--font-display)", fontWeight: 500 }}>Sofia</div>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--warm-500)" }}>
              Copiloto clínico
            </div>
          </div>
          {resposta && (
            <div style={{ marginLeft: "auto" }}>
              <CopiarBtn texto={resposta.resposta} className="btn btn-ghost" label="Copiar" />
            </div>
          )}
        </div>

        {/* Estado: carregando — respiração, não spinner */}
        {loading && (
          <div style={{ display: "flex", alignItems: "center", gap: 10, color: "var(--muted)" }}>
            <PresenceMark size={18} title="consultando" />
            <span>consultando o acervo…</span>
          </div>
        )}

        {/* Estado: erro */}
        {erro && <p style={{ color: "var(--danger)", margin: 0 }}>{erro}</p>}

        {/* Estado: resposta */}
        {resposta && (
          <>
            {resposta.sem_respaldo && (
              <div className="badge badge-warn" style={{ marginBottom: 10 }}>
                Sem respaldo direto no acervo — Sofia respondeu de forma geral.
              </div>
            )}

            <div
              style={{
                whiteSpace: "pre-wrap",
                color: "var(--ink-800)",
                lineHeight: 1.6,
              }}
            >
              {resposta.resposta}
              {streaming && (
                <span style={{ marginLeft: 4 }}><PresenceMark size={14} title="escrevendo" /></span>
              )}
            </div>

            {resposta.citacoes.length > 0 && (
              <div style={{ marginTop: 14 }}>
                <div
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: 11,
                    color: "var(--warm-500)",
                    marginBottom: 6,
                    display: "flex",
                    alignItems: "center",
                    gap: 6,
                  }}
                >
                  <BookOpen size={12} /> Fontes no acervo
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                  {resposta.citacoes.map((c) => (
                    <button
                      key={c.n}
                      type="button"
                      onClick={() => onCitacao?.(c)}
                      className="badge"
                      style={{ cursor: onCitacao ? "pointer" : "default", maxWidth: "100%" }}
                      title={`${c.titulo} — ${c.autor} · similaridade ${(c.similaridade * 100).toFixed(0)}%`}
                    >
                      <Quote size={12} /> T{c.n} · {c.titulo.slice(0, 40)}
                      <span style={{ fontFamily: "var(--font-mono)", color: "var(--warm-500)" }}>
                        {(c.similaridade * 100).toFixed(0)}%
                      </span>
                      {c.is_terceiro && (
                        <span className="badge badge-warn" style={{ padding: "1px 7px" }}>
                          paráfrase obrigatória
                        </span>
                      )}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {onUsarNaPreparacao && !streaming && (
              <div style={{ marginTop: 14 }}>
                <Button variant="ghost" onClick={onUsarNaPreparacao}>
                  <ClipboardCheck size={15} /> Usar na preparação de sessão
                </Button>
              </div>
            )}

            <p
              style={{
                marginTop: 14,
                marginBottom: 0,
                fontFamily: "var(--font-mono)",
                fontStyle: "italic",
                fontSize: 12,
                color: "var(--warm-500)",
              }}
            >
              {resposta.disclaimer} · <span className="badge badge-neutral">{resposta.modelo}</span>
            </p>
          </>
        )}
      </div>
    </div>
  );
}
