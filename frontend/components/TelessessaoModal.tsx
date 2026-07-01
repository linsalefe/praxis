"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Video, Link2, ShieldCheck, X } from "lucide-react";
import { api, ApiError, getToken } from "@/lib/api";
import { PresenceMark } from "@/components/ui/PresenceMark";
import { Skeleton } from "@/components/ui/Skeleton";

type SalaStatus = {
  sessao_id: string;
  modalidade: string;
  consentimento_teleatendimento: boolean;
  sala_url: string | null;
  link_paciente: string | null;
};

const TEXTO_CONSENTIMENTO =
  "Concordo em realizar o atendimento psicológico por meio de videochamada, " +
  "ciente de que o profissional zela pelo sigilo e por ambiente reservado, " +
  "conforme a Resolução CFP nº 11/2018 e atualizações.";

export function TelessessaoModal({
  sessaoId,
  pacienteId,
  pacienteNome,
  onClose,
}: {
  sessaoId: string;
  pacienteId: string;
  pacienteNome: string;
  onClose: () => void;
}) {
  const router = useRouter();
  const [status, setStatus] = useState<SalaStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [aceitoPor, setAceitoPor] = useState(pacienteNome);

  const carregar = useCallback(async () => {
    setLoading(true);
    try {
      setStatus(await api<SalaStatus>(`/sessoes/${sessaoId}/sala`));
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) return router.replace("/login");
      toast.error(err instanceof ApiError ? err.message : "Falha ao carregar a sala");
    } finally {
      setLoading(false);
    }
  }, [sessaoId, router]);

  useEffect(() => {
    if (!getToken()) return void router.replace("/login");
    carregar();
  }, [carregar, router]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape" && !busy) onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [busy, onClose]);

  async function registrarConsentimento() {
    if (aceitoPor.trim().length < 1) return;
    setBusy(true);
    try {
      await api("/consentimentos", {
        method: "POST",
        body: JSON.stringify({
          paciente_id: pacienteId,
          tipo: "teleatendimento",
          texto_aceito: TEXTO_CONSENTIMENTO,
          aceito_por: aceitoPor.trim(),
        }),
      });
      toast.success("Consentimento de teleatendimento registrado.");
      await carregar();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Falha ao registrar consentimento");
    } finally {
      setBusy(false);
    }
  }

  async function entrar() {
    setBusy(true);
    try {
      // Gera/obtém a sala (idempotente) e abre em nova aba.
      const s = await api<SalaStatus>(`/sessoes/${sessaoId}/sala`, { method: "POST" });
      setStatus(s);
      if (s.sala_url) window.open(s.sala_url, "_blank", "noopener");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Falha ao abrir a sala");
    } finally {
      setBusy(false);
    }
  }

  async function copiarLink() {
    let url = status?.link_paciente ?? null;
    if (!url) {
      try {
        const s = await api<SalaStatus>(`/sessoes/${sessaoId}/sala`, { method: "POST" });
        setStatus(s);
        url = s.link_paciente;
      } catch {
        return toast.error("Registre o consentimento antes de gerar o link.");
      }
    }
    if (!url) return;
    try {
      await navigator.clipboard.writeText(url);
      toast.success("Link do paciente copiado.");
    } catch {
      toast.error("Não foi possível copiar — copie manualmente: " + url);
    }
  }

  const temConsentimento = status?.consentimento_teleatendimento === true;

  return (
    <div
      role="dialog" aria-modal="true"
      style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 50 }}
      onClick={() => !busy && onClose()}
    >
      <div className="card" style={{ maxWidth: 520, width: "94%", background: "var(--surface)" }} onClick={(e) => e.stopPropagation()}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <PresenceMark size={20} />
            <h3 style={{ margin: 0 }}>Telessessão</h3>
          </div>
          <button className="btn" onClick={onClose} disabled={busy} aria-label="Fechar"><X size={16} /></button>
        </div>
        <p style={{ color: "var(--muted)", margin: "0 0 12px", fontSize: 13 }}>{pacienteNome}</p>

        <div style={{ display: "flex", gap: 8, alignItems: "flex-start", background: "var(--surface-2)", borderRadius: "var(--radius-md)", padding: 10, marginBottom: 14 }}>
          <ShieldCheck size={16} color="var(--brand-2)" style={{ flexShrink: 0, marginTop: 1 }} />
          <p style={{ margin: 0, fontSize: 12.5, color: "var(--muted)" }}>
            Atendimento por tecnologia (Res. CFP nº 11/2018): garanta ambiente reservado
            e conexão adequada. Gravação apenas com consentimento específico.
          </p>
        </div>

        {loading ? (
          <div style={{ display: "grid", gap: 10 }}>
            <Skeleton width="70%" height={14} />
            <Skeleton width="100%" height={38} />
          </div>
        ) : temConsentimento ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <button className="btn btn-primary" onClick={entrar} disabled={busy}>
              <Video size={16} /> {busy ? "Abrindo…" : "Entrar na sala"}
            </button>
            <button className="btn" onClick={copiarLink} disabled={busy}>
              <Link2 size={16} /> Copiar link do paciente
            </button>
            <p style={{ margin: "2px 0 0", fontSize: 11.5, color: "var(--muted)" }}>
              O paciente entra pelo mesmo link — não é preciso cadastro. A sala não expõe dados pessoais.
            </p>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <p style={{ margin: 0, fontSize: 14 }}>
              <strong>Consentimento de teleatendimento pendente.</strong> Registre o aceite do
              paciente antes de liberar a sala.
            </p>
            <p style={{ margin: 0, fontSize: 12.5, color: "var(--muted)", fontStyle: "italic" }}>
              “{TEXTO_CONSENTIMENTO}”
            </p>
            <div>
              <label className="label">Aceito por</label>
              <input className="input" value={aceitoPor} onChange={(e) => setAceitoPor(e.target.value)} placeholder="Nome de quem consente" />
            </div>
            <button className="btn btn-primary" onClick={registrarConsentimento} disabled={busy || aceitoPor.trim().length < 1}>
              <ShieldCheck size={16} /> {busy ? "Registrando…" : "Registrar consentimento"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
