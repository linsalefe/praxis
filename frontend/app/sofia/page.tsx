"use client";

import { useEffect, useRef, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { Send, BookOpen, MessageSquarePlus, History, Trash2 } from "lucide-react";
import { getToken } from "@/lib/api";
import { useSofiaChat, type Citacao } from "@/lib/useSofiaChat";
import { Topbar } from "@/components/Topbar";
import { PresenceMark } from "@/components/ui/PresenceMark";
import { SofiaOrientacao } from "@/components/ui/SofiaOrientacao";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Modal } from "@/components/ui/Modal";
import { Drawer } from "@/components/ui/Drawer";
import { PrepararSessaoModal } from "@/components/PrepararSessaoModal";

function PageInner() {
  const router = useRouter();
  const qs = useSearchParams();
  const pacienteId = qs.get("paciente_id");

  const [usarPaciente, setUsarPaciente] = useState<boolean>(!!pacienteId);
  const [pergunta, setPergunta] = useState("");
  const [drawer, setDrawer] = useState<Citacao | null>(null);
  const [prep, setPrep] = useState<string | null>(null);
  const [showHist, setShowHist] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const ultimoTurnoRef = useRef<HTMLDivElement>(null);

  const chat = useSofiaChat({
    pacienteId,
    usarPaciente,
    onUnauthorized: () => router.replace("/login"),
  });
  const { turnos, conversaId, historico, enviando } = chat;

  useEffect(() => {
    if (!getToken()) router.replace("/login");
  }, [router]);

  // Ao iniciar um novo turno, rola para o INÍCIO da última pergunta/resposta
  // (não para o fundo) — o profissional acompanha a resposta de cima para baixo.
  useEffect(() => {
    ultimoTurnoRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [turnos.length]);

  function submeter(e?: React.FormEvent | React.KeyboardEvent) {
    e?.preventDefault();
    const q = pergunta.trim();
    if (q.length < 3 || enviando) return;
    setPergunta("");
    void chat.enviar(q);
  }

  function abrirHistorico() {
    setShowHist(true);
    void chat.carregarHistorico();
  }

  async function abrirConversa(id: string) {
    if (await chat.abrirConversa(id)) {
      setShowHist(false);
      setDrawer(null);
    }
  }

  function excluirConversa(id: string, e: React.MouseEvent) {
    e.stopPropagation();
    void chat.excluirConversa(id);
  }

  function novaConversa() {
    chat.novaConversa();
    setDrawer(null);
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
            <span className="badge">respostas com fonte do acervo CENAT</span>
            <div style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
              <Button variant="ghost" onClick={abrirHistorico}>
                <History size={15} /> Histórico
              </Button>
              {turnos.length > 0 && (
                <Button variant="ghost" onClick={novaConversa}>
                  <MessageSquarePlus size={15} /> Nova conversa
                </Button>
              )}
            </div>
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
            <form onSubmit={submeter} style={{ display: "flex", gap: 8, alignItems: "flex-end" }}>
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
                    if (!enviando) submeter(e);
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
          <Modal open title={drawer.titulo} maxWidth={640} onClose={() => setDrawer(null)}>
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
          </Modal>
        )}

        {prep !== null && pacienteId && (
          <PrepararSessaoModal
            pacienteId={pacienteId}
            sofiaContexto={prep}
            onClose={() => setPrep(null)}
          />
        )}

        {showHist && (
          <Drawer open title="Histórico" onClose={() => setShowHist(false)}>
              {historico === null ? (
                <p style={{ color: "var(--muted)" }}>Carregando…</p>
              ) : historico.length === 0 ? (
                <p style={{ color: "var(--muted)" }}>Nenhuma conversa salva ainda.</p>
              ) : (
                <div style={{ display: "grid", gap: 8 }}>
                  {historico.map((c) => (
                    <div
                      key={c.id}
                      onClick={() => abrirConversa(c.id)}
                      className="card"
                      style={{
                        cursor: "pointer", display: "flex", alignItems: "flex-start", gap: 8,
                        padding: "10px 12px",
                        outline: c.id === conversaId ? "2px solid var(--brand-2)" : "none",
                      }}
                    >
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          {c.titulo}
                        </div>
                        <div style={{ color: "var(--muted)", fontSize: 12, marginTop: 2 }}>
                          {c.total_turnos} pergunta{c.total_turnos === 1 ? "" : "s"}
                          {c.paciente_id && <> · <span className="badge">paciente</span></>}
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={(e) => excluirConversa(c.id, e)}
                        aria-label="Excluir conversa"
                        style={{ border: "none", background: "transparent", cursor: "pointer", color: "var(--muted)", padding: 4 }}
                      >
                        <Trash2 size={15} />
                      </button>
                    </div>
                  ))}
                </div>
              )}
          </Drawer>
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
