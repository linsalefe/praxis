"use client";

/**
 * GraficoTrajetoria — mini-gráfico SVG leve (sem lib) da trajetória de uma escala.
 * Desenha só o que é factual: os escores registrados, com bandas de severidade ao
 * fundo (cores do InstrumentoFaixa). NÃO interpola nem rotula "melhora" — a leitura
 * é do profissional. Com 1 ponto, mostra o valor sem linha/tendência.
 */
import { corSeveridade } from "@/components/ui/InstrumentoFaixa";

export type FaixaDef = { min: number; max: number | null; rotulo: string; severidade: string };
export type PontoSerie = { data: string; escore: number; faixa: string | null; severidade: string | null; resposta_id: string };
export type SerieTrajetoria = {
  tipo: string; titulo: string; escore_min: number; escore_max: number;
  faixas: FaixaDef[]; pontos: PontoSerie[];
};

const fmtData = (iso: string) => new Date(iso).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" });

export function GraficoTrajetoria({ serie }: { serie: SerieTrajetoria }) {
  const W = 520, H = 150, padL = 32, padR = 14, padT = 12, padB = 24;
  const iw = W - padL - padR, ih = H - padT - padB;
  const { escore_min: ymin, escore_max: ymax, faixas, pontos } = serie;

  const yspan = ymax - ymin || 1;
  const yScale = (v: number) => padT + ih * (1 - (v - ymin) / yspan);

  const times = pontos.map((p) => new Date(p.data).getTime());
  const tmin = Math.min(...times), tmax = Math.max(...times);
  const tspan = tmax - tmin || 1;
  const um = pontos.length <= 1;
  const xScale = (t: number) => (um ? padL + iw / 2 : padL + iw * ((t - tmin) / tspan));

  const linha = pontos
    .map((p) => `${xScale(new Date(p.data).getTime()).toFixed(1)},${yScale(p.escore).toFixed(1)}`)
    .join(" ");

  const ultimo = pontos[pontos.length - 1];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 8 }}>
        <span style={{ fontFamily: "var(--font-display)", fontWeight: 500, fontSize: 14 }}>{serie.titulo}</span>
        <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--muted)" }}>
          {pontos.length} {pontos.length === 1 ? "registro" : "registros"}
        </span>
      </div>

      <svg
        viewBox={`0 0 ${W} ${H}`}
        width="100%"
        role="img"
        aria-label={`Trajetória de ${serie.titulo}: ${pontos.map((p) => `${fmtData(p.data)} escore ${p.escore}`).join(", ")}`}
        style={{ display: "block" }}
      >
        {/* Bandas de severidade (fundo) */}
        {faixas.map((f) => {
          const hi = f.max === null ? ymax : f.max;
          const yTop = yScale(hi), yBot = yScale(f.min);
          const c = corSeveridade(f.severidade);
          return (
            <rect
              key={f.rotulo}
              x={padL} y={yTop} width={iw} height={Math.max(0, yBot - yTop)}
              fill={c.bg} opacity={0.5}
            >
              <title>{`${f.rotulo} (${f.min}${f.max === null ? "+" : `–${f.max}`})`}</title>
            </rect>
          );
        })}

        {/* Eixo Y: min/max */}
        <text x={padL - 6} y={yScale(ymax) + 3} textAnchor="end" fontSize={9} fill="var(--muted)" fontFamily="var(--font-mono)">{ymax}</text>
        <text x={padL - 6} y={yScale(ymin) + 3} textAnchor="end" fontSize={9} fill="var(--muted)" fontFamily="var(--font-mono)">{ymin}</text>

        {/* Linha entre pontos (≥2) */}
        {!um && <polyline points={linha} fill="none" stroke="var(--ink-800)" strokeWidth={1.5} strokeLinejoin="round" strokeLinecap="round" opacity={0.55} />}

        {/* Pontos */}
        {pontos.map((p) => {
          const cx = xScale(new Date(p.data).getTime()), cy = yScale(p.escore);
          const c = corSeveridade(p.severidade);
          return (
            <g key={p.resposta_id}>
              <circle cx={cx} cy={cy} r={4.5} fill={c.fg} stroke="var(--surface)" strokeWidth={1.5}>
                <title>{`${fmtData(p.data)}: escore ${p.escore}${p.faixa ? ` (${p.faixa})` : ""}`}</title>
              </circle>
              <text x={cx} y={cy - 8} textAnchor="middle" fontSize={9} fontFamily="var(--font-mono)" fill={c.fg} fontWeight={600}>{p.escore}</text>
            </g>
          );
        })}

        {/* Eixo X: primeira/última data */}
        <text x={padL} y={H - 8} textAnchor="start" fontSize={9} fill="var(--muted)" fontFamily="var(--font-mono)">{fmtData(pontos[0].data)}</text>
        {!um && <text x={W - padR} y={H - 8} textAnchor="end" fontSize={9} fill="var(--muted)" fontFamily="var(--font-mono)">{fmtData(ultimo.data)}</text>}
      </svg>

      <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--muted)" }}>
        escores registrados · último: <span style={{ color: "var(--text)" }}>{ultimo.escore}</span>
        {ultimo.faixa && ` (${ultimo.faixa})`}
      </div>
    </div>
  );
}
