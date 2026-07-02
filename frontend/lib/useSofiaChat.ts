"use client";

/**
 * useSofiaChat — lógica de envio/streaming/histórico da Sofia, extraída de
 * app/sofia/page.tsx (Sprint W1) para reuso no painel do prontuário.
 *
 * Regra de ouro: comportamento idêntico ao da página original. O hook é dono
 * apenas do estado de conversa (turnos, conversa_id, histórico); estado de
 * *view* (input, modal de citação, drawer de histórico) fica em quem usa.
 */
import { useState } from "react";
import { toast } from "sonner";
import { api, ApiError, getToken } from "@/lib/api";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8040";

export type Citacao = {
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

export type Resp = {
  resposta: string;
  citacoes: Citacao[];
  sem_respaldo: boolean;
  usou_paciente: boolean;
  modelo: string;
  disclaimer: string;
  conversa_id?: string;
};

export type ConversaResumo = {
  id: string; titulo: string; paciente_id: string | null;
  total_turnos: number; criado_em: string; atualizado_em: string;
};

type TurnoHist = {
  pergunta: string; resposta: string; citacoes: Citacao[];
  sem_respaldo: boolean; usou_paciente: boolean; modelo: string | null;
  disclaimer: string; criado_em: string;
};

type ConversaDetalhe = {
  id: string; titulo: string; paciente_id: string | null;
  criado_em: string; turnos: TurnoHist[];
};

export type Turno = {
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

export type UseSofiaChat = {
  turnos: Turno[];
  setTurnos: React.Dispatch<React.SetStateAction<Turno[]>>;
  conversaId: string | null;
  historico: ConversaResumo[] | null;
  enviando: boolean;
  enviar: (pergunta: string) => Promise<void>;
  carregarHistorico: () => Promise<void>;
  abrirConversa: (id: string) => Promise<boolean>;
  excluirConversa: (id: string) => Promise<void>;
  novaConversa: () => void;
};

export function useSofiaChat(opts: {
  /** id do paciente a marcar como contexto, ou null. */
  pacienteId: string | null;
  /** toggle só-frontend: só envia paciente_id quando true. */
  usarPaciente: boolean;
  /** chamado em qualquer 401 (a página redireciona para /login). */
  onUnauthorized: () => void;
}): UseSofiaChat {
  const { pacienteId, usarPaciente, onUnauthorized } = opts;

  const [turnos, setTurnos] = useState<Turno[]>([]);
  const [conversaId, setConversaId] = useState<string | null>(null);
  const [historico, setHistorico] = useState<ConversaResumo[] | null>(null);

  const enviando = turnos.some((t) => t.loading || t.streaming);

  async function enviar(perguntaBruta: string) {
    const q = perguntaBruta.trim();
    if (q.length < 3 || enviando) return;
    const hora = new Date().toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
    setTurnos((ts) => [...ts, { pergunta: q, resposta: null, loading: true, hora }]);

    const body: Record<string, unknown> = { pergunta: q };
    if (usarPaciente && pacienteId) body.paciente_id = pacienteId;
    if (conversaId) body.conversa_id = conversaId;
    const patchLast = (patch: Partial<Turno>) =>
      setTurnos((ts) => ts.map((x, i) => (i === ts.length - 1 ? { ...x, ...patch } : x)));

    try {
      // Caminho principal: streaming SSE (primeira palavra em ~1s).
      const res = await fetch(`${API_BASE}/sofia/perguntar/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${getToken()}` },
        body: JSON.stringify(body),
      });
      if (res.status === 401) { onUnauthorized(); return; }
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
            const d = data as Omit<Resp, "resposta"> & { conversa_id?: string };
            if (d.conversa_id) setConversaId(d.conversa_id);
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
        if (r.conversa_id) setConversaId(r.conversa_id);
        patchLast({ loading: false, streaming: false, resposta: r });
      } catch (err) {
        const msg = err instanceof ApiError ? err.message : "Falha ao consultar Sofia";
        toast.error(msg);
        patchLast({ loading: false, streaming: false, erro: msg });
      }
    }
  }

  async function carregarHistorico() {
    setHistorico(null);
    try {
      setHistorico(await api<ConversaResumo[]>("/sofia/conversas"));
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) return onUnauthorized();
      toast.error("Não foi possível carregar o histórico.");
      setHistorico([]);
    }
  }

  /** Devolve true se a conversa foi aberta (para quem chama fechar a view). */
  async function abrirConversa(id: string): Promise<boolean> {
    try {
      const c = await api<ConversaDetalhe>(`/sofia/conversas/${id}`);
      setTurnos(
        c.turnos.map((t) => ({
          pergunta: t.pergunta,
          resposta: {
            resposta: t.resposta, citacoes: t.citacoes, sem_respaldo: t.sem_respaldo,
            usou_paciente: t.usou_paciente, modelo: t.modelo ?? "", disclaimer: t.disclaimer,
          },
          loading: false,
          hora: new Date(t.criado_em).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" }),
        })),
      );
      setConversaId(c.id);
      return true;
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) { onUnauthorized(); return false; }
      toast.error("Não foi possível abrir a conversa.");
      return false;
    }
  }

  async function excluirConversa(id: string) {
    try {
      await api(`/sofia/conversas/${id}`, { method: "DELETE" });
      setHistorico((h) => (h ? h.filter((c) => c.id !== id) : h));
      if (conversaId === id) { setTurnos([]); setConversaId(null); }
    } catch {
      toast.error("Não foi possível excluir a conversa.");
    }
  }

  function novaConversa() {
    setTurnos([]);
    setConversaId(null);
  }

  return {
    turnos, setTurnos, conversaId, historico, enviando,
    enviar, carregarHistorico, abrirConversa, excluirConversa, novaConversa,
  };
}
