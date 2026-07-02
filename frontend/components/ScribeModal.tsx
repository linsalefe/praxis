"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Mic, Upload, FileText, Square, X } from "lucide-react";
import { getToken, ApiError } from "@/lib/api";
import { PresenceMark } from "@/components/ui/PresenceMark";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";

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
  const [nivel, setNivel] = useState(0);            // U5: nível do mic (0..1)
  const [confirmarFechar, setConfirmarFechar] = useState(false);  // U4
  const mrRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const rafRef = useRef<number | null>(null);
  const stepTimersRef = useRef<ReturnType<typeof setTimeout>[]>([]);

  // Upload
  const fileRef = useRef<HTMLInputElement>(null);

  // U4: impede fechar a aba/janela com gravação em andamento ou áudio não enviado.
  const temAudioPendente = gravando || !!audioBlob;
  useEffect(() => {
    if (!temAudioPendente) return;
    const h = (e: BeforeUnloadEvent) => { e.preventDefault(); e.returnValue = ""; };
    window.addEventListener("beforeunload", h);
    return () => window.removeEventListener("beforeunload", h);
  }, [temAudioPendente]);

  // Limpa recursos de áudio ao desmontar.
  useEffect(() => () => {
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    audioCtxRef.current?.close().catch(() => {});
    stepTimersRef.current.forEach(clearTimeout);
  }, []);

  // U6: sequência estimada de etapas no cliente (a chamada de áudio faz
  // transcrição + estruturação no servidor numa única requisição).
  function iniciarEtapas(etapas: [string, number][]) {
    stepTimersRef.current.forEach(clearTimeout);
    stepTimersRef.current = [];
    etapas.forEach(([label, delay]) => {
      stepTimersRef.current.push(setTimeout(() => setBusy(label), delay));
    });
  }
  function pararEtapas() {
    stepTimersRef.current.forEach(clearTimeout);
    stepTimersRef.current = [];
  }

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

      // U5: medidor de nível via Web Audio.
      const Ctx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      const ctx = new Ctx();
      audioCtxRef.current = ctx;
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 256;
      ctx.createMediaStreamSource(stream).connect(analyser);
      analyserRef.current = analyser;
      const buf = new Uint8Array(analyser.frequencyBinCount);
      const tick = () => {
        analyser.getByteTimeDomainData(buf);
        let pico = 0;
        for (let i = 0; i < buf.length; i++) pico = Math.max(pico, Math.abs(buf[i] - 128));
        setNivel(Math.min(1, pico / 90));
        rafRef.current = requestAnimationFrame(tick);
      };
      tick();
    } catch (err) {
      toast.error("Permissão de microfone negada ou indisponível.");
    }
  }

  function pararGravacao() {
    mrRef.current?.stop();
    setGravando(false);
    if (timerRef.current) clearInterval(timerRef.current);
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    audioCtxRef.current?.close().catch(() => {});
    audioCtxRef.current = null;
    setNivel(0);
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
    // U6: etapas estimadas no cliente (a única requisição faz as duas fases no servidor).
    setBusy("Enviando áudio…");
    iniciarEtapas([["Transcrevendo…", 1500], ["Estruturando evolução…", 6000]]);
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
      pararEtapas();
      setBusy(null);
    }
  }

  function tentarFechar() {
    if (busy) return;
    if (temAudioPendente) { setConfirmarFechar(true); return; }
    onClose();
  }
  function descartarEFechar() {
    if (gravando) pararGravacao();
    setAudioBlob(null);
    setConfirmarFechar(false);
    onClose();
  }

  return (
    <>
    <div
      role="dialog"
      aria-modal="true"
      style={{
        position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)",
        display: "flex", alignItems: "center", justifyContent: "center", zIndex: 50,
      }}
      onClick={busy ? undefined : tentarFechar}
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
          <button className="btn" onClick={tentarFechar} disabled={!!busy} aria-label="Fechar">
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
                  <>
                    <button className="btn btn-danger" onClick={pararGravacao}>
                      <Square size={16} /> Parar ({duracao}s)
                    </button>
                    <span aria-live="polite" style={{ display: "inline-flex", alignItems: "center", gap: 6, color: "var(--danger)", fontSize: 13 }}>
                      <span className="rec-dot" aria-hidden style={{ width: 9, height: 9, borderRadius: "50%", background: "var(--danger)", display: "inline-block" }} />
                      gravando
                    </span>
                    {/* U5: nível do microfone */}
                    <span aria-hidden style={{ flex: 1, minWidth: 80, height: 8, background: "var(--sand-100)", borderRadius: 4, overflow: "hidden" }}>
                      <span style={{ display: "block", height: "100%", width: `${Math.round(nivel * 100)}%`, background: "var(--brand-2)", transition: "width 80ms linear" }} />
                    </span>
                  </>
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

    <ConfirmDialog
      open={confirmarFechar}
      title={gravando ? "Descartar gravação?" : "Descartar áudio?"}
      description={gravando
        ? "Há uma gravação em andamento. Se fechar agora, o áudio será perdido."
        : "Há um áudio gravado ainda não enviado. Se fechar agora, ele será perdido."}
      confirmLabel="Descartar e fechar"
      cancelLabel="Continuar"
      onConfirm={descartarEFechar}
      onCancel={() => setConfirmarFechar(false)}
    />
    </>
  );
}
