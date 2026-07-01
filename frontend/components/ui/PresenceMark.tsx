"use client";

/**
 * PresenceMark — a marca de presença do Práxis.
 * Arcos concêntricos que "respiram" (ciclo ~8s) em torno de um núcleo âmbar.
 * Substitui o clichê de IA (Sparkles/Wand2) nos momentos da Sofia/geração.
 *
 * Acessibilidade: sob `prefers-reduced-motion` a animação é congelada pelo
 * bloco global em globals.css; o estado de repouso (anéis a 0.9, núcleo sólido)
 * permanece legível e estático.
 */
export function PresenceMark({
  size = 24,
  className,
  title = "Sofia",
}: {
  size?: number;
  className?: string;
  title?: string;
}) {
  const ring = (delay: number, inset: number): React.CSSProperties => ({
    position: "absolute",
    inset,
    borderRadius: "var(--radius-full)",
    border: `${Math.max(1, size / 16)}px solid var(--teal-500)`,
    transform: "scale(0.9)",
    opacity: 0.9,
    transformOrigin: "center",
    animation: `presence-breathe var(--breath) var(--ease-calm) ${delay}s infinite`,
  });

  const core = size * 0.28;

  return (
    <span
      role="img"
      aria-label={title}
      className={className}
      style={{
        position: "relative",
        display: "inline-block",
        width: size,
        height: size,
        flex: "none",
        verticalAlign: "middle",
      }}
    >
      <span style={ring(0, 0)} />
      <span style={ring(-2.6, size * 0.18)} />
      <span
        style={{
          position: "absolute",
          top: "50%",
          left: "50%",
          width: core,
          height: core,
          marginTop: -core / 2,
          marginLeft: -core / 2,
          borderRadius: "var(--radius-full)",
          background: "var(--accent)",
          boxShadow: "0 0 0 2px var(--amber-100)",
        }}
      />
    </span>
  );
}
