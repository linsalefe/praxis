"use client";

/**
 * SofiaPainelProntuario — a Sofia embutida no prontuário como painel "sobre
 * este caso". Reusa useSofiaChat + SofiaOrientacao (mesmos endpoints da página
 * /sofia; nada de RAG/prompt muda aqui). Diferenças em relação à página:
 *  - contexto do paciente TRAVADO (usarPaciente sempre true); PII nunca vai à IA.
 *  - empty state com 3 sugestões geradas por regras determinísticas sobre os
 *    dados já carregados na página (instrumentos finalizados + escores).
 *  - ao abrir, reabre a última conversa deste paciente, se existir.
 *  - "Usar na preparação de sessão" é delegado à página (fecha o painel e abre
 *    o PrepararSessaoModal, que fica acima do drawer).
 */
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Send } from "lucide-react";
import { api } from "@/lib/api";
import { instrumentoTipoLabel } from "@/lib/labels";
import { useSofiaChat, type Citacao, type ConversaResumo } from "@/lib/useSofiaChat";
import { Drawer } from "@/components/ui/Drawer";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { PresenceMark } from "@/components/ui/PresenceMark";
import { SofiaOrientacao } from "@/components/ui/SofiaOrientacao";

type InstrFinalizavel = { instrumento_tipo: string; status: string; finalizado_em: string | null };
type SerieLike = {
  tipo: string; titulo: string;
  pontos: { severidade: string | null }[];
};

const SEVERIDADE_ALTA = new Set(["warn-strong", "risk"]);

const SUGESTOES_GERAIS = [
  "Como estruturar a primeira reunião de rede em Diálogo Aberto para este caso?",
  "Que princípios de redução de danos podem orientar o acompanhamento?",
  "Como o paradigma da atenção psicossocial ajuda a formular este caso?",
];

/**
 * Regras determinísticas (sem IA) sobre o estado factual já em memória.
 * Prioriza sinais do caso; completa com perguntas gerais do paradigma até 3.
 */
export function sugestoesDeterministicas(
  respostas: InstrFinalizavel[],
  series: SerieLike[],
): string[] {
  const out: string[] = [];

  // Regra A — escore recente em faixa alta → o que o acervo diz sobre o domínio.
  const serieAlta = series.find((s) => {
    const ultimo = s.pontos[s.pontos.length - 1];
    return ultimo && ultimo.severidade != null && SEVERIDADE_ALTA.has(ultimo.severidade);
  });
  if (serieAlta) {
    out.push(`O que o acervo indica diante de achados elevados em ${serieAlta.titulo}?`);
  }

  // Regra B — instrumento finalizado → como aprofundar os achados.
  const finalizados = respostas
    .filter((r) => r.status === "finalizado")
    .sort((a, b) => (b.finalizado_em ?? "").localeCompare(a.finalizado_em ?? ""));
  if (finalizados[0]) {
    out.push(`Como aprofundar os achados da ${instrumentoTipoLabel(finalizados[0].instrumento_tipo)}?`);
  }

  // Completa com gerais (sem duplicar) até 3.
  for (const g of SUGESTOES_GERAIS) {
    if (out.length >= 3) break;
    if (!out.includes(g)) out.push(g);
  }
  return out.slice(0, 3);
}

export function SofiaPainelProntuario({
  open,
  pacienteId,
  respostas,
  series,
  onClose,
  onUsarNaPreparacao,
}: {
  open: boolean;
  pacienteId: string;
  respostas: InstrFinalizavel[];
  series: SerieLike[];
  onClose: () => void;
  onUsarNaPreparacao: (contexto: string) => void;
}) {
  const router = useRouter();
  const [pergunta, setPergunta] = useState("");
  const [citacao, setCitacao] = useState<Citacao | null>(null);
  const [iniciado, setIniciado] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const ultimoTurnoRef = useRef<HTMLDivElement>(null);

  const chat = useSofiaChat({
    pacienteId,
    usarPaciente: true, // travado: painel é sempre sobre este paciente
    onUnauthorized: () => router.replace("/login"),
  });
  const { turnos, enviando } = chat;

  // Ao abrir pela primeira vez, reabre a última conversa deste paciente (se houver).
  useEffect(() => {
    if (!open || iniciado) return;
    setIniciado(true);
    (async () => {
      try {
        const convs = await api<ConversaResumo[]>("/sofia/conversas");
        const doPaciente = convs
          .filter((c) => c.paciente_id === pacienteId)
          .sort((a, b) => b.atualizado_em.localeCompare(a.atualizado_em));
        if (doPaciente[0]) await chat.abrirConversa(doPaciente[0].id);
      } catch {
        /* silencioso: começa uma conversa nova */
      }
    })();
  }, [open, iniciado, pacienteId, chat]);

  // Rola para o início do último turno quando um novo começa.
  useEffect(() => {
    ultimoTurnoRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [turnos.length]);

  function submeter(q: string) {
    const t = q.trim();
    if (t.length < 3 || enviando) return;
    setPergunta("");
    void chat.enviar(t);
  }

  const sugestoes = sugestoesDeterministicas(respostas, series);

  return (
    <Drawer open={open} title="Sofia · sobre este caso" onClose={onClose} width="min(480px, 100%)" flush>
      {/* Faixa de contexto / garantia de privacidade */}
      <div style={{
        display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap",
        padding: "8px 16px", borderBottom: "1px solid var(--border)", flexShrink: 0,
      }}>
        <span className="badge">contexto deste paciente</span>
        <span className="badge badge-warn">nada de PII vai à IA</span>
        {turnos.length > 0 && (
          <Button variant="ghost" onClick={chat.novaConversa} style={{ marginLeft: "auto" }}>
            Nova conversa
          </Button>
        )}
      </div>

      {/* Mensagens */}
      <div ref={scrollRef} style={{ flex: 1, minHeight: 0, overflowY: "auto", padding: "12px 16px" }}>
        {turnos.length === 0 ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <PresenceMark size={26} />
              <p style={{ margin: 0, color: "var(--muted)", fontSize: 14 }}>
                Pergunte sobre este caso — respostas fundamentadas no acervo CENAT, com citação da fonte.
              </p>
            </div>
            <div style={{ display: "grid", gap: 8 }}>
              {sugestoes.map((s) => (
                <button
                  key={s}
                  type="button"
                  className="card"
                  onClick={() => submeter(s)}
                  style={{ textAlign: "left", cursor: "pointer", padding: "10px 12px", lineHeight: 1.4 }}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          turnos.map((t, i) => (
            <div key={i} ref={i === turnos.length - 1 ? ultimoTurnoRef : undefined} style={{ scrollMarginTop: 8 }}>
              <SofiaOrientacao
                pergunta={t.pergunta}
                resposta={t.resposta}
                loading={t.loading}
                streaming={t.streaming}
                erro={t.erro}
                hora={t.hora}
                onCitacao={(c) => setCitacao(c)}
                onUsarNaPreparacao={() => onUsarNaPreparacao(t.resposta?.resposta ?? "")}
              />
            </div>
          ))
        )}
      </div>

      {/* Composer */}
      <div style={{ padding: "10px 16px", borderTop: "1px solid var(--border)", flexShrink: 0 }}>
        <form
          onSubmit={(e) => { e.preventDefault(); submeter(pergunta); }}
          style={{ display: "flex", gap: 8, alignItems: "flex-end" }}
        >
          <textarea
            className="input"
            placeholder="Pergunte sobre este caso…"
            value={pergunta}
            onChange={(e) => {
              setPergunta(e.target.value);
              e.target.style.height = "auto";
              e.target.style.height = `${Math.min(e.target.scrollHeight, 160)}px`;
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submeter(pergunta);
              }
            }}
            rows={1}
            style={{ resize: "none", minHeight: 40, lineHeight: 1.5, overflowY: "auto" }}
          />
          <Button variant="primary" type="submit" disabled={enviando || pergunta.trim().length < 3}>
            <Send size={16} />
          </Button>
        </form>
      </div>

      {/* Modal de citação — acima do drawer */}
      {citacao && (
        <Modal open title={citacao.titulo} maxWidth={640} elevated onClose={() => setCitacao(null)}>
          <p style={{ color: "var(--muted)", margin: "4px 0" }}>
            {citacao.autor}{citacao.editora ? ` · ${citacao.editora}` : ""}
          </p>
          <p style={{ margin: "4px 0" }}>
            {citacao.capitulo && <><span className="badge">cap. {citacao.capitulo}</span>{" "}</>}
            {citacao.pagina_inicio && (
              <><span className="badge">
                pp. {citacao.pagina_inicio}{citacao.pagina_fim && citacao.pagina_fim !== citacao.pagina_inicio ? `-${citacao.pagina_fim}` : ""}
              </span>{" "}</>
            )}
            {citacao.is_terceiro && (
              <span className="badge" style={{ color: "var(--brand-2)" }}>obra de terceiro — paráfrase</span>
            )}
          </p>
          <hr className="divider" />
          <p style={{ whiteSpace: "pre-wrap" }}>{citacao.snippet}</p>
          <div style={{ textAlign: "right", marginTop: 12 }}>
            <Button onClick={() => setCitacao(null)}>Fechar</Button>
          </div>
        </Modal>
      )}
    </Drawer>
  );
}
