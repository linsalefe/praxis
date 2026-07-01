"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Mic, Upload, FileText, Square, X } from "lucide-react";
import { getToken, ApiError } from "@/lib/api";
import { PresenceMark } from "@/components/ui/PresenceMark";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8040";

type Tab = "gravar" | "upload" | "resumo";

export function ScribeModal({
  sessaoId,
  onClose,
}: {
  sessaoId: string;
  onClose: () => void;
}) {
  const router = useRouter();
  const [tab, setTab] = useState<Tab>("resumo");
  const [busy, setBusy] = useState<string | null>(null);
  const [texto, setTexto] = useState("");

  // Gravação
  const [gravando, setGravando] = useState(false);
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [duracao, setDuracao] = useState(0);
  const mrRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Upload
  const fileRef = useRef<HTMLInputElement>(null);

  async function iniciarGravacao() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      chunksRef.current = [];
      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : "audio/webm";
      const mr = new MediaRecorder(stream, { mimeType });
      mr.ondataavailable = (e) => e.data.size > 0 && chunksRef.current.push(e.data);
      mr.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        setAudioBlob(blob);
        streamRef.current?.getTracks().forEach((t) => t.stop());
        streamRef.current = null;
      };
      mr.start(1000);
      mrRef.current = mr;
      setGravando(true);
      setDuracao(0);
      timerRef.current = setInterval(() => setDuracao((d) => d + 1), 1000);
    } catch (err) {
      toast.error("Permissão de microfone negada ou indisponível.");
    }
  }

  function pararGravacao() {
    mrRef.current?.stop();
    setGravando(false);
    if (timerRef.current) clearInterval(timerRef.current);
  }

  async function enviarResumo() {
    if (texto.trim().length < 10) {
      toast.error("Digite pelo menos 10 caracteres.");
      return;
    }
    setBusy("Estruturando…");
    try {
      const res = await fetch(`${API_BASE}/sessoes/${sessaoId}/scribe/resumo`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({ texto }),
      });
      const data = await res.json();
      if (!res.ok) throw new ApiError(res.status, data.detail || "Falha");
      toast.success(`Rascunho pronto (${data.latencia_ms} ms).`);
      router.push(`/evolucoes/${data.evolucao_id}`);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Falha ao gerar");
    } finally {
      setBusy(null);
    }
  }

  async function enviarAudio(blob: Blob, filename: string) {
    setBusy("Transcrevendo áudio…");
    try {
      const form = new FormData();
      form.append("file", blob, filename);
      const res = await fetch(`${API_BASE}/sessoes/${sessaoId}/scribe/audio`, {
        method: "POST",
        headers: { Authorization: `Bearer ${getToken()}` },
        body: form,
      });
      const data = await res.json();
      if (!res.ok) throw new ApiError(res.status, data.detail || "Falha");
      toast.success(`Rascunho pronto. Áudio deletado (${data.provider_transc}).`);
      router.push(`/evolucoes/${data.evolucao_id}`);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "Falha ao processar áudio";
      toast.error(msg);
    } finally {
      setBusy(null);
    }
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      style={{
        position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)",
        display: "flex", alignItems: "center", justifyContent: "center", zIndex: 50,
      }}
      onClick={busy ? undefined : onClose}
    >
      <div
        className="card"
        style={{ width: "92%", maxWidth: 640, background: "var(--surface)" }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h3 style={{ margin: 0, display: "flex", alignItems: "center", gap: 8 }}>
            <PresenceMark size={18} /> Gerar evolução
          </h3>
          <button className="btn" onClick={onClose} disabled={!!busy} aria-label="Fechar">
            <X size={14} />
          </button>
        </div>

        <div style={{ display: "flex", gap: 6, marginTop: 12, borderBottom: "1px solid var(--border)" }}>
          {(
            [
              ["resumo", <><FileText key="i" size={14} /> Resumo</>],
              ["upload", <><Upload key="i" size={14} /> Anexar áudio</>],
              ["gravar", <><Mic key="i" size={14} /> Gravar</>],
            ] as [Tab, React.ReactNode][]
          ).map(([k, lab]) => (
            <button
              key={k}
              type="button"
              onClick={() => setTab(k)}
              style={{
                background: "transparent", border: 0, color: tab === k ? "var(--brand-2)" : "var(--muted)",
                padding: "8px 12px", cursor: "pointer",
                borderBottom: `2px solid ${tab === k ? "var(--brand-2)" : "transparent"}`,
                display: "inline-flex", alignItems: "center", gap: 6, fontSize: 14,
              }}
              disabled={!!busy}
            >
              {lab}
            </button>
          ))}
        </div>

        <div style={{ marginTop: 16 }}>
          {tab === "resumo" && (
            <>
              <p style={{ color: "var(--muted)", fontSize: 13 }}>
                Digite ou dite um resumo da sessão. O Scribe estrutura nos 4 blocos CFP e devolve como rascunho.
              </p>
              <textarea
                className="input"
                rows={8}
                placeholder="Ex.: Sessão com Ana, primeira consulta. Trouxe queixa de ansiedade e insônia há 3 meses…"
                value={texto}
                onChange={(e) => setTexto(e.target.value)}
                disabled={!!busy}
              />
              <div style={{ marginTop: 12, textAlign: "right" }}>
                <button className="btn btn-primary" onClick={enviarResumo} disabled={!!busy}>
                  <PresenceMark size={16} /> {busy ?? "Gerar evolução"}
                </button>
              </div>
            </>
          )}

          {tab === "upload" && (
            <>
              <p style={{ color: "var(--muted)", fontSize: 13 }}>
                Aceita mp3, m4a, wav, webm, ogg, opus, flac. Áudio &gt; 25 MB é re-encodado antes da transcrição.
                Requer consentimento de <strong>gravação</strong> registrado para este paciente.
              </p>
              <input
                ref={fileRef}
                type="file"
                accept="audio/*"
                className="input"
                disabled={!!busy}
              />
              <div style={{ marginTop: 12, textAlign: "right" }}>
                <button
                  className="btn btn-primary"
                  disabled={!!busy}
                  onClick={async () => {
                    const f = fileRef.current?.files?.[0];
                    if (!f) return toast.error("Selecione um arquivo.");
                    await enviarAudio(f, f.name);
                  }}
                >
                  <Upload size={16} /> {busy ?? "Enviar e transcrever"}
                </button>
              </div>
            </>
          )}

          {tab === "gravar" && (
            <>
              <p style={{ color: "var(--muted)", fontSize: 13 }}>
                Grava direto no navegador (opus/webm). Requer consentimento de <strong>gravação</strong>.
              </p>
              <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                {!gravando && !audioBlob && (
                  <button className="btn btn-primary" onClick={iniciarGravacao} disabled={!!busy}>
                    <Mic size={16} /> Iniciar
                  </button>
                )}
                {gravando && (
                  <button className="btn btn-danger" onClick={pararGravacao}>
                    <Square size={16} /> Parar ({duracao}s)
                  </button>
                )}
                {audioBlob && !gravando && (
                  <>
                    <span className="badge">gravado {duracao}s · {(audioBlob.size / 1024).toFixed(0)} KB</span>
                    <button className="btn" onClick={() => { setAudioBlob(null); setDuracao(0); }} disabled={!!busy}>
                      Descartar
                    </button>
                    <button
                      className="btn btn-primary"
                      disabled={!!busy}
                      onClick={() => enviarAudio(audioBlob, `sessao-${sessaoId}.webm`)}
                    >
                      <PresenceMark size={16} /> {busy ?? "Enviar e gerar"}
                    </button>
                  </>
                )}
              </div>
            </>
          )}
        </div>

        {busy && (
          <p style={{ marginTop: 12, color: "var(--muted)", fontSize: 12 }}>
            {busy} · o áudio será apagado do servidor assim que a transcrição terminar.
          </p>
        )}
        <p style={{ marginTop: 12, color: "var(--muted)", fontSize: 11 }}>
          Rascunho é editável. Assinatura permanece manual — a responsabilidade técnica é do profissional (Manual CFP 2025).
        </p>
      </div>
    </div>
  );
}
