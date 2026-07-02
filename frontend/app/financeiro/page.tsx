"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Wallet, Receipt, Download } from "lucide-react";
import { api, ApiError, getToken } from "@/lib/api";
import { formatCentavos } from "@/lib/money";
import { Topbar } from "@/components/Topbar";
import { PresenceMark } from "@/components/ui/PresenceMark";
import { SkeletonCard } from "@/components/ui/Skeleton";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Field } from "@/components/ui/Field";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8040";

type Lancamento = {
  sessao_id: string; paciente_id: string; paciente_nome: string; data: string;
  valor_centavos: number; status: "pendente" | "pago";
  forma: string | null; pago_em: string | null;
  recibo: { id: string; numero: number } | null;
};

const FORMAS = [
  { v: "pix", l: "Pix" }, { v: "dinheiro", l: "Dinheiro" },
  { v: "cartao", l: "Cartão" }, { v: "transferencia", l: "Transferência" },
];

function hojeISO() {
  return new Date().toISOString().slice(0, 10);
}

/** Baixa um PDF autenticado (o api() só faz JSON) e abre em nova aba. */
async function abrirPdf(path: string, method: "GET" | "POST", body?: unknown) {
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: {
      Authorization: `Bearer ${getToken()}`,
      ...(body ? { "Content-Type": "application/json" } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new ApiError(res.status, `Falha ao gerar PDF (${res.status})`);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  window.open(url, "_blank");
  setTimeout(() => URL.revokeObjectURL(url), 60_000);
}

export default function FinanceiroPage() {
  const router = useRouter();
  const [lancs, setLancs] = useState<Lancamento[]>([]);
  const [loading, setLoading] = useState(true);
  const [de, setDe] = useState("");
  const [ate, setAte] = useState("");

  const [pagar, setPagar] = useState<Lancamento | null>(null);
  const [forma, setForma] = useState("pix");
  const [pagoEm, setPagoEm] = useState(hojeISO());
  const [busy, setBusy] = useState(false);

  const [reciboDe, setReciboDe] = useState<Lancamento | null>(null);

  const carregar = useCallback(async () => {
    setLoading(true);
    try {
      const qs = new URLSearchParams();
      if (de) qs.set("de", de);
      if (ate) qs.set("ate", ate);
      const s = qs.toString();
      setLancs(await api<Lancamento[]>(`/financeiro/pagamentos${s ? `?${s}` : ""}`));
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) router.replace("/login");
    } finally {
      setLoading(false);
    }
  }, [de, ate, router]);

  useEffect(() => {
    if (!getToken()) return void router.replace("/login");
    carregar();
  }, [carregar, router]);

  const pendentes = lancs.filter((l) => l.status === "pendente");
  const pagos = lancs.filter((l) => l.status === "pago");
  const totalPendente = pendentes.reduce((a, l) => a + l.valor_centavos, 0);

  async function confirmarPagamento() {
    if (!pagar) return;
    setBusy(true);
    try {
      await api(`/financeiro/pagamentos/${pagar.sessao_id}`, {
        method: "POST",
        body: JSON.stringify({ forma, pago_em: new Date(pagoEm).toISOString() }),
      });
      toast.success("Pagamento registrado.");
      setPagar(null);
      setForma("pix");
      setPagoEm(hojeISO());
      await carregar();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Falha ao registrar");
    } finally {
      setBusy(false);
    }
  }

  async function confirmarRecibo() {
    if (!reciboDe) return;
    setBusy(true);
    try {
      await abrirPdf("/financeiro/recibos", "POST", { sessao_id: reciboDe.sessao_id });
      toast.success("Recibo emitido.");
      setReciboDe(null);
      await carregar();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Falha ao emitir recibo");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <Topbar />
      <main className="container-praxis" style={{ maxWidth: 920 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
          <PresenceMark size={26} />
          <h1 style={{ margin: 0, fontSize: 22 }}>Financeiro</h1>
          <Wallet size={18} color="var(--brand-2)" />
        </div>
        <p style={{ color: "var(--muted)", margin: "0 0 16px", fontSize: 14 }}>
          Valores registrados por sessão — nada de projeção. Recibo é comprovante para reembolso
          de plano (não é nota fiscal).
        </p>

        <div style={{ display: "flex", gap: 8, alignItems: "end", marginBottom: 18, flexWrap: "wrap" }}>
          <Field label="De">
            <input className="input" type="date" value={de} onChange={(e) => setDe(e.target.value)} />
          </Field>
          <Field label="Até">
            <input className="input" type="date" value={ate} onChange={(e) => setAte(e.target.value)} />
          </Field>
          {(de || ate) && (
            <Button onClick={() => { setDe(""); setAte(""); }}>Limpar período</Button>
          )}
        </div>

        {loading ? (
          <div style={{ display: "grid", gap: 12 }}>
            <SkeletonCard lines={2} />
            <SkeletonCard lines={2} />
          </div>
        ) : (
          <>
            {/* Pendências */}
            <h2 style={{ fontSize: 15, color: "var(--muted)", margin: "0 0 10px" }}>
              Pendências
              {pendentes.length > 0 && (
                <span style={{ marginLeft: 8, color: "var(--text)" }}>
                  {pendentes.length} sessão{pendentes.length > 1 ? "es" : ""} pendente
                  {pendentes.length > 1 ? "s" : ""} · {formatCentavos(totalPendente)}
                </span>
              )}
            </h2>
            {pendentes.length === 0 ? (
              <Card><p style={{ margin: 0, color: "var(--muted)" }}>
                Nenhuma sessão realizada aguardando pagamento no período.
              </p></Card>
            ) : (
              <div style={{ display: "grid", gap: 10 }}>
                {pendentes.map((l) => (
                  <Card key={l.sessao_id} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
                    <div>
                      <div style={{ fontWeight: 500 }}>{l.paciente_nome}</div>
                      <div style={{ color: "var(--muted)", fontSize: 13 }}>
                        {new Date(l.data).toLocaleDateString("pt-BR")} · {formatCentavos(l.valor_centavos)}
                      </div>
                    </div>
                    <Button variant="primary" onClick={() => setPagar(l)}>Marcar pago</Button>
                  </Card>
                ))}
              </div>
            )}

            {/* Pagos / histórico */}
            <h2 style={{ fontSize: 15, color: "var(--muted)", margin: "24px 0 10px" }}>Pagos</h2>
            {pagos.length === 0 ? (
              <Card><p style={{ margin: 0, color: "var(--muted)" }}>
                Nenhum pagamento registrado no período.
              </p></Card>
            ) : (
              <div style={{ display: "grid", gap: 10 }}>
                {pagos.map((l) => (
                  <Card key={l.sessao_id} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
                    <div>
                      <div style={{ fontWeight: 500 }}>{l.paciente_nome}</div>
                      <div style={{ color: "var(--muted)", fontSize: 13 }}>
                        {new Date(l.data).toLocaleDateString("pt-BR")} · {formatCentavos(l.valor_centavos)}
                        {l.forma && <> · {l.forma}</>}
                      </div>
                    </div>
                    {l.recibo ? (
                      <Button onClick={() => abrirPdf(`/financeiro/recibos/${l.recibo!.id}`, "GET").catch(() => toast.error("Falha ao baixar"))}>
                        <Download size={15} /> Recibo nº {l.recibo.numero}
                      </Button>
                    ) : (
                      <Button variant="primary" onClick={() => setReciboDe(l)}>
                        <Receipt size={15} /> Emitir recibo
                      </Button>
                    )}
                  </Card>
                ))}
              </div>
            )}
          </>
        )}
      </main>

      {/* Modal: marcar pago (forma + data) */}
      {pagar && (
        <div
          role="dialog" aria-modal="true"
          style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.4)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 40 }}
          onClick={() => !busy && setPagar(null)}
        >
          <Card style={{ maxWidth: 420, width: "92%", background: "var(--surface)" }} onClick={(e) => e.stopPropagation()}>
            <h3 style={{ marginTop: 0 }}>Registrar pagamento</h3>
            <p style={{ color: "var(--muted)", margin: "4px 0 14px", fontSize: 14 }}>
              {pagar.paciente_nome} · {formatCentavos(pagar.valor_centavos)}
            </p>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
              <Field label="Forma">
                <select className="input" value={forma} onChange={(e) => setForma(e.target.value)}>
                  {FORMAS.map((f) => <option key={f.v} value={f.v}>{f.l}</option>)}
                </select>
              </Field>
              <Field label="Pago em">
                <input className="input" type="date" value={pagoEm} onChange={(e) => setPagoEm(e.target.value)} />
              </Field>
            </div>
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 16 }}>
              <Button onClick={() => setPagar(null)} disabled={busy}>Cancelar</Button>
              <Button variant="primary" onClick={confirmarPagamento} loading={busy}>
                {busy ? "Salvando…" : "Confirmar pagamento"}
              </Button>
            </div>
          </Card>
        </div>
      )}

      {/* Confirmação: emitir recibo (número sequencial e definitivo) */}
      <ConfirmDialog
        open={!!reciboDe}
        title="Emitir recibo"
        description={reciboDe ? `Emitir recibo para ${reciboDe.paciente_nome} no valor de ${formatCentavos(reciboDe.valor_centavos)}? O número é sequencial e definitivo.` : ""}
        confirmLabel="Emitir e baixar PDF"
        busy={busy}
        onConfirm={confirmarRecibo}
        onCancel={() => setReciboDe(null)}
      />
    </>
  );
}
