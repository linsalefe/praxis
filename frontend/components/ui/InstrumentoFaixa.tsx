"use client";

/**
 * InstrumentoFaixa — faixa de progresso/estado de um instrumento.
 * Os instrumentos do Práxis (Maastricht, WRAP) são qualitativos: não há escore
 * numérico nem faixa de severidade no modelo. Esta faixa reflete apenas dados
 * reais — avanço por seções e status — sem fabricar interpretação clínica.
 */
export function InstrumentoFaixa({
  titulo,
  versao,
  status,
  atual,
  total,
  unidade = "seções",
}: {
  titulo: string;
  versao?: string;
  status: string;
  atual: number;
  total: number;
  unidade?: string;
}) {
  const finalizado = status === "finalizado";
  const segsPreenchidos = Math.max(0, Math.min(atual, total));

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
        <div style={{ fontFamily: "var(--font-display)", fontWeight: 500 }}>
          {titulo}
          {versao && (
            <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--warm-500)" }}>
              {" "}· {versao}
            </span>
          )}
        </div>
        <span className={`badge ${finalizado ? "badge-pos" : "badge-info"}`}>
          {finalizado ? "finalizado" : "em andamento"}
        </span>
      </div>

      {/* Barra segmentada por seção */}
      <div
        role="progressbar"
        aria-valuenow={segsPreenchidos}
        aria-valuemin={0}
        aria-valuemax={total}
        style={{ display: "flex", gap: 3, height: 8 }}
      >
        {Array.from({ length: Math.max(1, total) }).map((_, i) => (
          <span
            key={i}
            style={{
              flex: 1,
              borderRadius: "var(--radius-full)",
              background:
                i < segsPreenchidos
                  ? finalizado
                    ? "var(--pos-fg)"
                    : "var(--teal-500)"
                  : "var(--sand-100)",
              transition: "background var(--dur-base) var(--ease-calm)",
            }}
          />
        ))}
      </div>

      <div style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--warm-500)" }}>
        {segsPreenchidos}/{total} {unidade}
      </div>
    </div>
  );
}

/**
 * FaixaSeveridade — banda de severidade para escalas quantitativas (likert_sum).
 * O escore e a faixa vêm CALCULADOS do backend (factuais). Este componente só
 * desenha: um segmento por faixa (mínimo→grave), com a faixa vigente destacada
 * e o escore em fonte mono. Não recalcula nada no cliente.
 */
export type FaixaDef = { min: number; max: number | null; rotulo: string; severidade: string };

const SEV: Record<string, { fg: string; bg: string; line: string }> = {
  pos: { fg: "var(--pos-fg)", bg: "var(--pos-bg)", line: "var(--pos-line)" },
  sage: { fg: "var(--sage-600)", bg: "var(--sage-100)", line: "var(--sage-300)" },
  warn: { fg: "var(--warn-fg)", bg: "var(--warn-bg)", line: "var(--warn-line)" },
  "warn-strong": { fg: "#7a4a12", bg: "var(--warn-bg)", line: "var(--warn-line)" },
  risk: { fg: "var(--risk-fg)", bg: "var(--risk-bg)", line: "var(--risk-line)" },
};

/** Cores semânticas da severidade (fonte única, reusada pela trajetória). */
export const corSeveridade = (s?: string | null) => (s && SEV[s]) || SEV.warn;
const sevOf = corSeveridade;

export function FaixaSeveridade({
  rotulo,
  escore,
  escoreBruto,
  faixas,
  faixaRotulo,
  severidade,
  completo,
}: {
  rotulo: string;
  escore: number | null;
  escoreBruto?: number | null;
  faixas: FaixaDef[];
  faixaRotulo: string | null;
  severidade: string | null;
  completo: boolean;
}) {
  const c = sevOf(severidade);
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 8 }}>
        <span style={{ fontFamily: "var(--font-display)", fontWeight: 500, fontSize: 14 }}>{rotulo}</span>
        <span>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 20, fontWeight: 600, color: completo ? c.fg : "var(--warm-500)" }}>
            {escore ?? "—"}
          </span>
          {typeof escoreBruto === "number" && escoreBruto !== escore && (
            <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--warm-500)" }}> (bruto {escoreBruto})</span>
          )}
        </span>
      </div>

      {/* Banda: um segmento por faixa; a vigente fica preenchida. */}
      <div style={{ display: "flex", gap: 3, height: 10 }} role="img" aria-label={`Faixa: ${faixaRotulo ?? "incompleta"}`}>
        {faixas.map((f) => {
          const ativa = completo && f.rotulo === faixaRotulo;
          const fc = sevOf(f.severidade);
          return (
            <span
              key={f.rotulo}
              title={`${f.rotulo} (${f.min}${f.max === null ? "+" : `–${f.max}`})`}
              style={{
                flex: 1,
                borderRadius: "var(--radius-full)",
                background: ativa ? fc.fg : fc.bg,
                border: `1px solid ${fc.line}`,
                transition: "background var(--dur-base) var(--ease-calm)",
              }}
            />
          );
        })}
      </div>

      <div style={{ fontSize: 12 }}>
        {completo ? (
          <span className="badge" style={{ background: c.bg, borderColor: c.line, color: c.fg }}>
            {faixaRotulo}
          </span>
        ) : (
          <span style={{ fontFamily: "var(--font-mono)", color: "var(--warm-500)" }}>
            faixa preliminar — responda todos os itens
          </span>
        )}
      </div>
    </div>
  );
}
