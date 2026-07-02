"use client";

import ReactMarkdown, { type Components } from "react-markdown";
import rehypeSanitize from "rehype-sanitize";
import { BookOpen, ClipboardCheck, Quote } from "lucide-react";
import { PresenceMark } from "@/components/ui/PresenceMark";
import { CopiarBtn } from "@/components/ui/CopiarBtn";
import { Button } from "@/components/ui/Button";

/**
 * Corpo da resposta em Markdown, estilizado no design system.
 * Marcadores [Tn] no texto viram `[Tn](#cite-n)` e são renderizados como
 * superscript clicável que abre a citação correspondente. Links externos são
 * neutralizados (renderizados como texto) — nada navega para fora.
 */
function RespostaMarkdown({ texto, onCitacaoN }: { texto: string; onCitacaoN?: (n: number) => void }) {
  const preparado = texto.replace(/\[T(\d+)\]/g, "[T$1](#cite-$1)");

  const componentes: Components = {
    p: ({ children }) => <p style={{ margin: "0 0 10px", lineHeight: 1.6 }}>{children}</p>,
    ul: ({ children }) => <ul style={{ margin: "0 0 10px", paddingLeft: 20 }}>{children}</ul>,
    ol: ({ children }) => <ol style={{ margin: "0 0 10px", paddingLeft: 20 }}>{children}</ol>,
    li: ({ children }) => <li style={{ marginBottom: 4, lineHeight: 1.55 }}>{children}</li>,
    strong: ({ children }) => <strong style={{ fontWeight: 600 }}>{children}</strong>,
    em: ({ children }) => <em>{children}</em>,
    h1: ({ children }) => <h4 style={{ fontFamily: "var(--font-display)", fontSize: 15, margin: "12px 0 6px" }}>{children}</h4>,
    h2: ({ children }) => <h4 style={{ fontFamily: "var(--font-display)", fontSize: 15, margin: "12px 0 6px" }}>{children}</h4>,
    h3: ({ children }) => <h4 style={{ fontFamily: "var(--font-display)", fontSize: 14, margin: "10px 0 6px" }}>{children}</h4>,
    h4: ({ children }) => <h4 style={{ fontFamily: "var(--font-display)", fontSize: 14, margin: "10px 0 6px" }}>{children}</h4>,
    code: ({ children }) => (
      <code style={{ fontFamily: "var(--font-mono)", fontSize: "0.9em", background: "var(--surface-2)", padding: "1px 5px", borderRadius: 4 }}>{children}</code>
    ),
    a: ({ href, children }) => {
      const m = /^#cite-(\d+)$/.exec(href ?? "");
      if (m) {
        const n = Number(m[1]);
        return (
          <sup>
            <button
              type="button"
              onClick={() => onCitacaoN?.(n)}
              className="link"
              style={{ background: "none", border: "none", padding: 0, cursor: "pointer", fontFamily: "var(--font-mono)", fontSize: "0.85em" }}
              title={`Ver fonte T${n}`}
            >
              [T{n}]
            </button>
          </sup>
        );
      }
      // Link externo neutralizado — mantém só o texto.
      return <span>{children}</span>;
    },
  };

  return (
    <ReactMarkdown rehypePlugins={[rehypeSanitize]} components={componentes}>
      {preparado}
    </ReactMarkdown>
  );
}

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
  hora,
  onCitacao,
  onUsarNaPreparacao,
}: {
  pergunta: string;
  resposta: SofiaRespostaBase<C> | null;
  loading?: boolean;
  streaming?: boolean;
  erro?: string;
  hora?: string;
  onCitacao?: (c: C) => void;
  onUsarNaPreparacao?: () => void;
}) {
  return (
    <div style={{ marginBottom: 24 }}>
      {/* Pergunta do profissional — bolha distinta, alinhada à direita */}
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 10 }}>
        <div style={{ maxWidth: "85%" }}>
          <div style={{ color: "var(--muted)", fontSize: 12, marginBottom: 2, textAlign: "right" }}>Você</div>
          <div style={{
            background: "var(--surface-2)",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius-lg)",
            padding: "8px 12px",
            whiteSpace: "pre-wrap",
          }}>{pergunta}</div>
        </div>
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
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--muted)" }}>
              Copiloto clínico
            </div>
          </div>
          {resposta && (
            <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 8 }}>
              {hora && (
                <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--muted)" }}>{hora}</span>
              )}
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

            <div style={{ color: "var(--ink-800)" }}>
              <RespostaMarkdown
                texto={resposta.resposta}
                onCitacaoN={(n) => {
                  const c = resposta.citacoes.find((x) => x.n === n);
                  if (c) onCitacao?.(c);
                }}
              />
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
                    color: "var(--muted)",
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
                      title={`${c.titulo} — ${c.autor}`}
                    >
                      <Quote size={12} /> T{c.n} · {c.titulo.slice(0, 48)}
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
                color: "var(--muted)",
              }}
            >
              {resposta.disclaimer}
            </p>
          </>
        )}
      </div>
    </div>
  );
}
