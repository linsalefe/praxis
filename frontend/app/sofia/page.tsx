"use client";

import { useEffect, useRef, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import { Send, BookOpen, MessageSquarePlus } from "lucide-react";
import { api, ApiError, getToken } from "@/lib/api";
import { Topbar } from "@/components/Topbar";
import { PresenceMark } from "@/components/ui/PresenceMark";
import { SofiaOrientacao } from "@/components/ui/SofiaOrientacao";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { PrepararSessaoModal } from "@/components/PrepararSessaoModal";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8040";

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
  streaming?: boolean;
  erro?: string;
  hora: string;
};

const RESP_VAZIA: Resp = {
  resposta: "", citacoes: [], sem_respaldo: false, usou_paciente: false, modelo: "", disclaimer: "",
};

function parseSSE(block: string): { event: string; data: unknown } {
  let event = "";
  let data = "";
  for (const line of block.split("\n")) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) data += line.slice(5).trim();
  }
  return { event, data: data ? JSON.parse(data) : null };
}

function PageInner() {
  const router = useRouter();
  const qs = useSearchParams();
  const pacienteId = qs.get("paciente_id");

  const [usarPaciente, setUsarPaciente] = useState<boolean>(!!pacienteId);
  const [pergunta, setPergunta] = useState("");
  const [turnos, setTurnos] = useState<Turno[]>([]);
  const [drawer, setDrawer] = useState<Citacao | null>(null);
  const [prep, setPrep] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const ultimoTurnoRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!getToken()) router.replace("/login");
  }, [router]);

  // Ao iniciar um novo turno, rola para o INÍCIO da última pergunta/resposta
  // (não para o fundo) — o profissional acompanha a resposta de cima para baixo.
  useEffect(() => {
    ultimoTurnoRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [turnos.length]);

  const enviando = turnos.some((t) => t.loading || t.streaming);

  async function enviar(e?: React.FormEvent | React.KeyboardEvent) {
    e?.preventDefault();
    const q = pergunta.trim();
    if (q.length < 3 || enviando) return;
    setPergunta("");
    const hora = new Date().toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
    setTurnos((ts) => [...ts, { pergunta: q, resposta: null, loading: true, hora }]);

    const body: Record<string, unknown> = { pergunta: q };
    if (usarPaciente && pacienteId) body.paciente_id = pacienteId;
    const patchLast = (patch: Partial<Turno>) =>
      setTurnos((ts) => ts.map((x, i) => (i === ts.length - 1 ? { ...x, ...patch } : x)));

    try {
      // Caminho principal: streaming SSE (primeira palavra em ~1s).
      const res = await fetch(`${API_BASE}/sofia/perguntar/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${getToken()}` },
        body: JSON.stringify(body),
      });
      if (res.status === 401) { router.replace("/login"); return; }
      if (!res.ok || !res.body) throw new Error("stream indisponível");

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";
      let acc = "";
      let concluido = false;

      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const blocos = buf.split("\n\n");
        buf = blocos.pop() ?? "";
        for (const bloco of blocos) {
          if (!bloco.trim()) continue;
          const { event, data } = parseSSE(bloco);
          if (event === "token") {
            acc += (data as { delta: string }).delta;
            patchLast({ loading: false, streaming: true, resposta: { ...RESP_VAZIA, resposta: acc } });
          } else if (event === "done") {
            const d = data as Omit<Resp, "resposta">;
            patchLast({ loading: false, streaming: false, resposta: { ...d, resposta: acc } });
            concluido = true;
          } else if (event === "error") {
            throw new Error((data as { message?: string })?.message || "Falha ao consultar Sofia");
          }
        }
      }
      if (!concluido) throw new Error("resposta incompleta");
    } catch {
      // Fallback: endpoint não-stream — mantém a Sofia funcional se o SSE falhar.
      try {
        const r = await api<Resp>("/sofia/perguntar", { method: "POST", body: JSON.stringify(body) });
        patchLast({ loading: false, streaming: false, resposta: r });
      } catch (err) {
        const msg = err instanceof ApiError ? err.message : "Falha ao consultar Sofia";
        toast.error(msg);
        patchLast({ loading: false, streaming: false, erro: msg });
      }
    }
  }

  return (
    <>
      <div style={{ display: "flex", flexDirection: "column", height: "100dvh" }}>
        <Topbar />
        <main
          style={{
            flex: 1, minHeight: 0, width: "100%", maxWidth: 900,
            margin: "0 auto", padding: "16px 24px 0",
            display: "flex", flexDirection: "column",
          }}
        >
          {/* Cabeçalho fixo */}
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
            <PresenceMark size={26} />
            <h1 style={{ margin: 0, fontSize: 22 }}>Sofia</h1>
            <span className="badge">acervo CENAT · RAG</span>
            {turnos.length > 0 && (
              <Button
                variant="ghost"
                onClick={() => { setTurnos([]); setDrawer(null); }}
                style={{ marginLeft: "auto" }}
              >
                <MessageSquarePlus size={15} /> Nova conversa
              </Button>
            )}
          </div>
          {pacienteId && (
            <label style={{ fontSize: 13, color: "var(--muted)", marginBottom: 8, display: "inline-flex", alignItems: "center", gap: 6 }}>
              <input
                type="checkbox"
                checked={usarPaciente}
                onChange={(e) => setUsarPaciente(e.target.checked)}
              />
              marcar contexto deste paciente <span className="badge">nada de PII vai à IA</span>
            </label>
          )}

          {/* Mensagens — área rolável que ocupa a altura disponível */}
          <div
            ref={scrollRef}
            style={{ flex: 1, minHeight: 0, overflowY: "auto", padding: "8px 2px" }}
          >
            {turnos.length === 0 && (
              <p style={{ color: "var(--muted)" }}>
                Faça perguntas clínicas — as respostas são fundamentadas no acervo, com citação da fonte. Ex.:
                “Como estruturar a primeira reunião de rede em Diálogo Aberto?”,
                “O que a literatura diz sobre redução de danos com clozapina?”
              </p>
            )}
            {turnos.map((t, i) => (
              <div key={i} ref={i === turnos.length - 1 ? ultimoTurnoRef : undefined} style={{ scrollMarginTop: 8 }}>
                <SofiaOrientacao
                  pergunta={t.pergunta}
                  resposta={t.resposta}
                  loading={t.loading}
                  streaming={t.streaming}
                  erro={t.erro}
                  hora={t.hora}
                  onCitacao={(c) => setDrawer(c)}
                  onUsarNaPreparacao={pacienteId ? () => setPrep(t.resposta?.resposta ?? "") : undefined}
                />
              </div>
            ))}
          </div>

          {/* Composer fixo na base */}
          <div style={{ paddingTop: 8, paddingBottom: 12, borderTop: "1px solid var(--border)" }}>
            <form onSubmit={enviar} style={{ display: "flex", gap: 8, alignItems: "flex-end" }}>
              <textarea
                className="input"
                placeholder="Pergunte à Sofia…"
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
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 6 }}>
              <span style={{ fontSize: 11, color: "var(--muted)" }}>
                <kbd>Enter</kbd> envia · <kbd>Shift+Enter</kbd> quebra linha
              </span>
              <Link className="link" href="/sofia/acervo" style={{ fontSize: 12 }}>
                <BookOpen size={12} style={{ display: "inline", verticalAlign: "middle" }} /> Ver acervo indexado
              </Link>
            </div>
          </div>

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
                {drawer.capitulo && <><span className="badge">cap. {drawer.capitulo}</span>{" "}</>}
                {drawer.pagina_inicio && (
                  <><span className="badge">
                    pp. {drawer.pagina_inicio}{drawer.pagina_fim && drawer.pagina_fim !== drawer.pagina_inicio ? `-${drawer.pagina_fim}` : ""}
                  </span>{" "}</>
                )}
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

        {prep !== null && pacienteId && (
          <PrepararSessaoModal
            pacienteId={pacienteId}
            sofiaContexto={prep}
            onClose={() => setPrep(null)}
          />
        )}
        </main>
      </div>
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
