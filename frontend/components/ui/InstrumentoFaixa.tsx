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
