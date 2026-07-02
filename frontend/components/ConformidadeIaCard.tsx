"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { toast } from "sonner";
import { ShieldCheck, Cpu, Check } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { Skeleton } from "@/components/ui/Skeleton";

type Consentimento = { id: string; tipo: string; aceito_por: string; aceito_em: string };
type IaLogItem = { acao: string; recurso: string; ts: string | null; entidade: string; entidade_id: string | null };
type Tcle = { versao: string; texto: string };

export function ConformidadeIaCard({
  pacienteId,
  pacienteNome,
}: {
  pacienteId: string;
  pacienteNome: string;
}) {
  const [consentimentos, setConsentimentos] = useState<Consentimento[] | null>(null);
  const [iaLog, setIaLog] = useState<IaLogItem[] | null>(null);
  const [busy, setBusy] = useState(false);

  const carregar = useCallback(async () => {
    try {
      const [cons, log] = await Promise.all([
        api<Consentimento[]>(`/consentimentos/paciente/${pacienteId}`),
        api<IaLogItem[]>(`/pacientes/${pacienteId}/ia-log`),
      ]);
      setConsentimentos(cons);
      setIaLog(log);
    } catch {
      setConsentimentos([]);
      setIaLog([]);
    }
  }, [pacienteId]);

  useEffect(() => { carregar(); }, [carregar]);

  const usoIa = consentimentos?.find((c) => c.tipo === "uso_ia") ?? null;

  async function registrar() {
    setBusy(true);
    try {
      const tcle = await api<Tcle>("/consentimentos/tcle-ia");
      await api("/consentimentos", {
        method: "POST",
        body: JSON.stringify({
          paciente_id: pacienteId,
          tipo: "uso_ia",
          texto_aceito: tcle.texto,
          aceito_por: pacienteNome,
        }),
      });
      toast.success("Consentimento de uso de IA registrado.");
      await carregar();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Falha ao registrar consentimento");
    } finally {
      setBusy(false);
    }
  }

  const loading = consentimentos === null || iaLog === null;

  return (
    <div className="card" style={{ marginTop: 20 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
        <ShieldCheck size={16} color="var(--brand-2)" />
        <h2 style={{ fontSize: 15, margin: 0 }}>Conformidade IA (Res. CFP 09/2024)</h2>
      </div>

      {loading ? (
        <div style={{ display: "grid", gap: 8, marginTop: 10 }}>
          <Skeleton width="60%" height={14} />
          <Skeleton width="40%" height={14} />
        </div>
      ) : (
        <>
          {/* Status do consentimento de uso de IA */}
          <div style={{ margin: "8px 0 14px" }}>
            {usoIa ? (
              <span style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 13, color: "var(--pos-fg, var(--text))" }}>
                <Check size={15} color="var(--brand-2)" />
                Consentimento de uso de IA registrado em {new Date(usoIa.aceito_em).toLocaleDateString("pt-BR")} · por {usoIa.aceito_por}
              </span>
            ) : (
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
                <span style={{ fontSize: 13, color: "var(--muted)" }}>
                  Consentimento de uso de IA ainda não registrado para este paciente.
                </span>
                <button className="btn btn-primary" onClick={registrar} disabled={busy}>
                  {busy ? "Registrando…" : "Registrar TCLE de IA"}
                </button>
              </div>
            )}
          </div>

          {/* Log factual de uso de IA */}
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 6 }}>
            <Cpu size={14} color="var(--muted)" />
            <span style={{ fontSize: 13, color: "var(--muted)" }}>Uso de IA neste prontuário</span>
          </div>
          {iaLog.length === 0 ? (
            <p style={{ margin: 0, fontSize: 13, color: "var(--muted)" }}>
              Nenhum uso de IA registrado para este paciente ainda.
            </p>
          ) : (
            <ul style={{ margin: 0, paddingLeft: 18, display: "grid", gap: 4 }}>
              {iaLog.map((ev, i) => (
                <li key={i} style={{ fontSize: 13 }}>
                  <span style={{ fontFamily: "var(--font-mono)", color: "var(--muted)" }}>
                    {ev.ts ? new Date(ev.ts).toLocaleDateString("pt-BR") : "—"}
                  </span>{" "}
                  · {ev.recurso}
                </li>
              ))}
            </ul>
          )}
          <p style={{ margin: "10px 0 0", fontSize: 11.5, color: "var(--muted)" }}>
            Uso de IA de apoio — todo conteúdo é rascunho revisado e assinado pelo profissional.{" "}
            <Link className="link" href="/como-usamos-ia" target="_blank">Como o Práxis usa IA</Link>
          </p>
        </>
      )}
    </div>
  );
}
