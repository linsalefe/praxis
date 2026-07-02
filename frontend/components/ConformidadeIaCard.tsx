"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { toast } from "sonner";
import { ShieldCheck, Cpu, Check } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { Skeleton } from "@/components/ui/Skeleton";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Drawer } from "@/components/ui/Drawer";
import { Field } from "@/components/ui/Field";

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
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [tcle, setTcle] = useState<Tcle | null>(null);
  const [loadingTcle, setLoadingTcle] = useState(false);
  const [aceitoPor, setAceitoPor] = useState(pacienteNome);
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

  async function abrirDrawer() {
    setAceitoPor(pacienteNome);
    setDrawerOpen(true);
    if (tcle) return;
    setLoadingTcle(true);
    try {
      setTcle(await api<Tcle>("/consentimentos/tcle-ia"));
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Falha ao carregar o termo");
    } finally {
      setLoadingTcle(false);
    }
  }

  async function registrar() {
    if (!tcle || aceitoPor.trim().length < 1) return;
    setBusy(true);
    try {
      await api("/consentimentos", {
        method: "POST",
        body: JSON.stringify({
          paciente_id: pacienteId,
          tipo: "uso_ia",
          texto_aceito: tcle.texto,
          aceito_por: aceitoPor.trim(),
        }),
      });
      toast.success("Consentimento de uso de IA registrado.");
      setDrawerOpen(false);
      await carregar();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Falha ao registrar consentimento");
    } finally {
      setBusy(false);
    }
  }

  const loading = consentimentos === null || iaLog === null;

  return (
    <Card style={{ marginTop: 20 }}>
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
                <Button variant="primary" onClick={abrirDrawer}>Registrar TCLE de IA</Button>
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

      <Drawer
        open={drawerOpen}
        title="Consentimento de uso de IA"
        onClose={() => { if (!busy) setDrawerOpen(false); }}
      >
        <p style={{ margin: 0, fontSize: 13, color: "var(--muted)" }}>
          Leia o termo com o paciente antes de registrar o aceite. O texto é gravado
          junto do consentimento (Res. CFP 09/2024).
        </p>

        {loadingTcle || !tcle ? (
          <div style={{ display: "grid", gap: 8 }}>
            <Skeleton width="100%" height={14} />
            <Skeleton width="92%" height={14} />
            <Skeleton width="96%" height={14} />
            <Skeleton width="70%" height={14} />
          </div>
        ) : (
          <>
            <p style={{ margin: 0, fontSize: 13, color: "var(--text)", fontStyle: "italic", lineHeight: 1.55, whiteSpace: "pre-wrap" }}>
              “{tcle.texto}”
            </p>
            <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--muted)" }}>
              versão {tcle.versao}
            </span>
            <Field label="Aceito por">
              <input
                className="input"
                value={aceitoPor}
                onChange={(e) => setAceitoPor(e.target.value)}
                placeholder="Nome de quem consente"
              />
            </Field>
            <Button
              variant="primary"
              onClick={registrar}
              loading={busy}
              loadingLabel="Registrando…"
              disabled={aceitoPor.trim().length < 1}
            >
              <ShieldCheck size={16} /> Registrar consentimento
            </Button>
          </>
        )}
      </Drawer>
    </Card>
  );
}
