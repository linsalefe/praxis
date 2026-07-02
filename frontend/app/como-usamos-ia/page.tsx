import Link from "next/link";
import { ShieldCheck, Check, X } from "lucide-react";
import { PresenceMark } from "@/components/ui/PresenceMark";
import { Card } from "@/components/ui/Card";

export const metadata = {
  title: "Como o Práxis usa IA · CENAT",
  description:
    "Transparência sobre o uso de inteligência artificial de apoio no Práxis, " +
    "em conformidade com a Res. CFP 09/2024 e a Nota de Posicionamento do CFP sobre IA.",
};

// Página pública (sem autenticação) — material de transparência e confiança.
export default function ComoUsamosIaPage() {
  const faz = [
    "Transcreve e organiza rascunhos de evolução a partir de áudio ou resumo (Scribe).",
    "Sugere raciocínio clínico com base no acervo, sempre com citação da fonte (Sofia).",
    "Ajuda a preparar sessões e a interpretar instrumentos — como rascunho.",
  ];
  const naoFaz = [
    "Não decide nem substitui o julgamento do(a) profissional.",
    "Não fecha diagnóstico nem prescreve conduta.",
    "Não dispensa a revisão e a assinatura humana de todo conteúdo.",
  ];

  return (
    <main className="container-praxis" style={{ maxWidth: 760 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 8, marginBottom: 6 }}>
        <PresenceMark size={26} />
        <h1 style={{ margin: 0, fontSize: 24 }}>Como o Práxis usa IA</h1>
      </div>
      <p style={{ color: "var(--muted)", margin: "0 0 20px", fontSize: 15, lineHeight: 1.5 }}>
        No Práxis (by CENAT), a inteligência artificial é <strong>ferramenta de apoio</strong> ao
        profissional de psicologia — nunca uma substituta. Todo conteúdo gerado é um{" "}
        <strong>rascunho</strong> que o(a) profissional revisa, edita e <strong>assina</strong>.
        A responsabilidade técnica pela conduta é sempre humana.
      </p>

      <Card style={{ marginBottom: 16 }}>
        <h2 style={{ fontSize: 16, marginTop: 0 }}>O que a IA faz</h2>
        <ul style={{ margin: 0, paddingLeft: 4, listStyle: "none", display: "grid", gap: 8 }}>
          {faz.map((t, i) => (
            <li key={i} style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
              <Check size={16} color="var(--brand-2)" style={{ flexShrink: 0, marginTop: 2 }} />
              <span>{t}</span>
            </li>
          ))}
        </ul>
      </Card>

      <Card style={{ marginBottom: 16 }}>
        <h2 style={{ fontSize: 16, marginTop: 0 }}>O que a IA não faz</h2>
        <ul style={{ margin: 0, paddingLeft: 4, listStyle: "none", display: "grid", gap: 8 }}>
          {naoFaz.map((t, i) => (
            <li key={i} style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
              <X size={16} color="var(--muted)" style={{ flexShrink: 0, marginTop: 2 }} />
              <span>{t}</span>
            </li>
          ))}
        </ul>
      </Card>

      <Card style={{ marginBottom: 16, display: "flex", gap: 10, alignItems: "flex-start" }}>
        <ShieldCheck size={18} color="var(--brand-2)" style={{ flexShrink: 0, marginTop: 2 }} />
        <div>
          <h2 style={{ fontSize: 16, margin: "0 0 6px" }}>Supervisão humana e confidencialidade</h2>
          <p style={{ margin: 0, color: "var(--muted)", fontSize: 14, lineHeight: 1.5 }}>
            Seguimos a <strong>Resolução CFP nº 09/2024</strong> (responsabilidade técnica do
            psicólogo e informação/consentimento sobre o tratamento de dados com IA) e a{" "}
            <strong>Nota de Posicionamento do CFP sobre Inteligência Artificial (julho/2025)</strong>,
            que reforçam a supervisão humana obrigatória e a confidencialidade. Os dados são
            tratados conforme a LGPD, e cada paciente pode registrar seu consentimento informado
            sobre o uso de IA de apoio. Todo uso de IA fica registrado e é exportável no pacote
            de dados do paciente.
          </p>
        </div>
      </Card>

      <p style={{ color: "var(--muted)", fontSize: 13, marginTop: 20 }}>
        <Link className="link" href="/login">← Entrar no Práxis</Link>
      </p>
    </main>
  );
}
