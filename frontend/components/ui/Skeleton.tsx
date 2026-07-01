"use client";

/**
 * Skeleton — placeholder calmo durante carregamentos.
 * Bloco em --sand-100 com shimmer suave; sob prefers-reduced-motion a animação
 * é congelada (bloco estático) pelo bloco global em globals.css.
 */
export function Skeleton({
  width = "100%",
  height = 16,
  radius = "var(--radius-md)",
  style,
}: {
  width?: number | string;
  height?: number | string;
  radius?: number | string;
  style?: React.CSSProperties;
}) {
  return (
    <span
      aria-hidden
      style={{
        display: "block",
        width,
        height,
        borderRadius: radius,
        background:
          "linear-gradient(90deg, var(--sand-100) 25%, var(--surface-2) 50%, var(--sand-100) 75%)",
        backgroundSize: "180% 100%",
        animation: "presence-shimmer 1.6s var(--ease-calm) infinite",
        ...style,
      }}
    />
  );
}

/** Linhas de skeleton para um card genérico. */
export function SkeletonCard({ lines = 3 }: { lines?: number }) {
  return (
    <div className="card" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      <Skeleton width="40%" height={14} />
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton key={i} width={i === lines - 1 ? "70%" : "100%"} height={12} />
      ))}
    </div>
  );
}
