"use client";

/**
 * PacienteCard — cabeçalho do prontuário.
 * Avatar com iniciais, identificação e meta em mono. "Adesão" é factual, com
 * denominador explícito: realizadas ÷ (realizadas + faltas) — mesma definição
 * do resumo longitudinal. Omitida quando não há sessões que deveriam ter ocorrido.
 */

type PacienteLike = {
  nome: string;
  contato: string | null;
  nascimento: string | null;
  documento: string | null;
  sexo: string | null;
};
type SessaoLike = { data: string; status: string };

function iniciais(nome: string): string {
  const partes = nome.trim().split(/\s+/).filter(Boolean);
  if (partes.length === 0) return "?";
  if (partes.length === 1) return partes[0].slice(0, 2).toUpperCase();
  return (partes[0][0] + partes[partes.length - 1][0]).toUpperCase();
}

function idade(nascimento: string | null): number | null {
  if (!nascimento) return null;
  const n = new Date(nascimento);
  if (Number.isNaN(n.getTime())) return null;
  const hoje = new Date();
  let a = hoje.getFullYear() - n.getFullYear();
  const m = hoje.getMonth() - n.getMonth();
  if (m < 0 || (m === 0 && hoje.getDate() < n.getDate())) a--;
  return a >= 0 && a < 150 ? a : null;
}

function Meta({ rotulo, valor }: { rotulo: string; valor: string }) {
  return (
    <div>
      <div style={{ fontSize: 11, color: "var(--muted)" }}>{rotulo}</div>
      <div style={{ fontFamily: "var(--font-mono)", fontSize: 14, color: "var(--text)" }}>{valor}</div>
    </div>
  );
}

export function PacienteCard({
  paciente,
  sessoes,
}: {
  paciente: PacienteLike;
  sessoes: SessaoLike[];
}) {
  const ini = iniciais(paciente.nome);
  const anos = idade(paciente.nascimento);
  const agora = new Date();

  const proxima = sessoes
    .filter((s) => s.status === "agendada" && new Date(s.data) >= agora)
    .sort((a, b) => +new Date(a.data) - +new Date(b.data))[0];

  const realizadas = sessoes.filter((s) => s.status === "realizada").length;
  const faltas = sessoes.filter((s) => s.status === "falta").length;
  const baseAdesao = realizadas + faltas; // sessões que deveriam ter ocorrido

  const identificacao = [
    anos != null ? `${anos} anos` : null,
    paciente.sexo,
    paciente.documento,
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <div className="card" style={{ padding: 0, overflow: "hidden" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 16, padding: 20 }}>
        <div
          aria-hidden
          style={{
            width: 56,
            height: 56,
            flex: "none",
            borderRadius: "var(--radius-full)",
            background: "var(--teal-100)",
            color: "var(--teal-700)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontFamily: "var(--font-display)",
            fontSize: 20,
            fontWeight: 600,
          }}
        >
          {ini}
        </div>
        <div style={{ minWidth: 0, flex: 1 }}>
          <h1 style={{ fontSize: 22, margin: "0 0 4px" }}>{paciente.nome}</h1>
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            <span className="badge badge-info">Em acompanhamento</span>
            <span style={{ color: "var(--muted)", fontSize: 13 }}>
              {identificacao || "Sem dados adicionais."}
            </span>
          </div>
        </div>
      </div>

      <div
        style={{
          display: "flex",
          gap: 32,
          padding: "12px 20px",
          borderTop: "1px solid var(--border)",
          background: "var(--surface-2)",
        }}
      >
        <Meta rotulo="Sessões" valor={String(sessoes.length)} />
        <Meta
          rotulo="Próxima"
          valor={proxima ? new Date(proxima.data).toLocaleDateString("pt-BR") : "—"}
        />
        <Meta rotulo="Adesão" valor={baseAdesao > 0 ? `${realizadas}/${baseAdesao}` : "—"} />
      </div>
    </div>
  );
}
