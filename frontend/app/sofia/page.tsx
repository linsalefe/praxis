"use client";

import { useEffect, useRef, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import { Send, BookOpen } from "lucide-react";
import { api, ApiError, getToken } from "@/lib/api";
import { Topbar } from "@/components/Topbar";
import { PresenceMark } from "@/components/ui/PresenceMark";
import { SofiaOrientacao } from "@/components/ui/SofiaOrientacao";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";

type Citacao = {
  n: number;
  documento_id: string;
  slug: string;
  titulo: string;
  autor: string;
  editora: string | null;
  is_terceiro: boolean;
  capitulo: string | null;
  pagina_inicio: number | null;
  pagina_fim: number | null;
  snippet: string;
  similaridade: number;
};

type Resp = {
  resposta: string;
  citacoes: Citacao[];
  sem_respaldo: boolean;
  usou_paciente: boolean;
  modelo: string;
  disclaimer: string;
};

type Turno = {
  pergunta: string;
  resposta: Resp | null;
  loading: boolean;
  erro?: string;
};

function PageInner() {
  const router = useRouter();
  const qs = useSearchParams();
  const pacienteId = qs.get("paciente_id");

  const [usarPaciente, setUsarPaciente] = useState<boolean>(!!pacienteId);
  const [pergunta, setPergunta] = useState("");
  const [turnos, setTurnos] = useState<Turno[]>([]);
  const [drawer, setDrawer] = useState<Citacao | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!getToken()) router.replace("/login");
  }, [router]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [turnos]);

  const enviando = turnos.some((t) => t.loading);

  async function enviar(e?: React.FormEvent | React.KeyboardEvent) {
    e?.preventDefault();
    const q = pergunta.trim();
    if (q.length < 3 || enviando) return;
    setPergunta("");
    const t: Turno = { pergunta: q, resposta: null, loading: true };
    setTurnos((ts) => [...ts, t]);
    try {
      const body: Record<string, unknown> = { pergunta: q };
      if (usarPaciente && pacienteId) body.paciente_id = pacienteId;
      const r = await api<Resp>("/sofia/perguntar", { method: "POST", body: JSON.stringify(body) });
      setTurnos((ts) => ts.map((x, i) => (i === ts.length - 1 ? { ...x, loading: false, resposta: r } : x)));
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "Falha ao consultar Sofia";
      toast.error(msg);
      setTurnos((ts) => ts.map((x, i) => (i === ts.length - 1 ? { ...x, loading: false, erro: msg } : x)));
    }
  }

  return (
    <>
      <Topbar />
      <main className="container-praxis" style={{ maxWidth: 900 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
          <PresenceMark size={26} />
          <h1 style={{ margin: 0, fontSize: 22 }}>Sofia</h1>
          <span className="badge">acervo CENAT · RAG</span>
        </div>
        <p style={{ color: "var(--muted)", margin: "0 0 16px", fontSize: 14 }}>
          Faça perguntas clínicas. As respostas são fundamentadas no acervo e trazem citação da fonte.
          {pacienteId && (
            <>
              {" "}
              <label style={{ marginLeft: 8 }}>
                <input
                  type="checkbox"
                  checked={usarPaciente}
                  onChange={(e) => setUsarPaciente(e.target.checked)}
                />{" "}
                marcar contexto deste paciente <span className="badge">nada de PII vai à IA</span>
              </label>
            </>
          )}
        </p>

        <div
          ref={scrollRef}
          className="card"
          style={{ minHeight: 360, maxHeight: "62vh", overflowY: "auto", padding: 16 }}
        >
          {turnos.length === 0 && (
            <p style={{ color: "var(--muted)" }}>
              Ex.: “Como estruturar a primeira reunião de rede em Diálogo Aberto?”,
              “O que a literatura diz sobre redução de danos com clozapina?”
            </p>
          )}
          {turnos.map((t, i) => (
            <SofiaOrientacao
              key={i}
              pergunta={t.pergunta}
              resposta={t.resposta}
              loading={t.loading}
              erro={t.erro}
              onCitacao={(c) => setDrawer(c)}
            />
          ))}
        </div>

        <form onSubmit={enviar} style={{ display: "flex", gap: 8, marginTop: 12, alignItems: "flex-end" }}>
          <textarea
            className="input"
            placeholder="Pergunte à Sofia…  (Enter envia · Shift+Enter quebra linha)"
            value={pergunta}
            onChange={(e) => {
              setPergunta(e.target.value);
              e.target.style.height = "auto";
              e.target.style.height = `${Math.min(e.target.scrollHeight, 200)}px`;
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                if (!enviando) enviar(e);
              }
            }}
            rows={1}
            style={{ resize: "none", minHeight: 40, lineHeight: 1.5, overflowY: "auto" }}
          />
          <Button variant="primary" type="submit" disabled={enviando || pergunta.trim().length < 3}>
            <Send size={16} /> Enviar
          </Button>
        </form>

        <p style={{ marginTop: 12, fontSize: 12, color: "var(--muted)" }}>
          <Link className="link" href="/sofia/acervo">
            <BookOpen size={12} style={{ display: "inline", verticalAlign: "middle" }} /> Ver acervo indexado
          </Link>
        </p>

        {drawer && (
          <div
            role="dialog"
            aria-modal="true"
            style={{
              position: "fixed", inset: 0, background: "rgba(0,0,0,0.4)",
              display: "flex", alignItems: "center", justifyContent: "center", zIndex: 40,
            }}
            onClick={() => setDrawer(null)}
          >
            <Card
              style={{ maxWidth: 640, width: "92%", background: "var(--surface)" }}
              onClick={(e) => e.stopPropagation()}
            >
              <h3 style={{ marginTop: 0 }}>{drawer.titulo}</h3>
              <p style={{ color: "var(--muted)", margin: "4px 0" }}>
                {drawer.autor}{drawer.editora ? ` · ${drawer.editora}` : ""}
              </p>
              <p style={{ margin: "4px 0" }}>
                <span className="badge">cap. {drawer.capitulo || "n/d"}</span>{" "}
                <span className="badge">
                  {drawer.pagina_inicio ? `pp. ${drawer.pagina_inicio}${drawer.pagina_fim && drawer.pagina_fim !== drawer.pagina_inicio ? `-${drawer.pagina_fim}` : ""}` : "p. n/d"}
                </span>{" "}
                <span className="badge">sim {(drawer.similaridade * 100).toFixed(0)}%</span>
                {drawer.is_terceiro && (
                  <span className="badge" style={{ color: "var(--brand-2)" }}>obra de terceiro — paráfrase</span>
                )}
              </p>
              <hr className="divider" />
              <p style={{ whiteSpace: "pre-wrap" }}>{drawer.snippet}</p>
              <div style={{ textAlign: "right", marginTop: 12 }}>
                <Button onClick={() => setDrawer(null)}>Fechar</Button>
              </div>
            </Card>
          </div>
        )}
      </main>
    </>
  );
}

export default function SofiaPage() {
  return (
    <Suspense fallback={<main className="container-praxis"><p style={{ color: "var(--muted)" }}>Carregando…</p></main>}>
      <PageInner />
    </Suspense>
  );
}
