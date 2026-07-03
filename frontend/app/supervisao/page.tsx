"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import { Compass, PlusCircle, Trash2, Users2 } from "lucide-react";
import { api, ApiError, getToken } from "@/lib/api";
import { Topbar } from "@/components/Topbar";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import { SupervisaoModal } from "@/components/SupervisaoModal";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";

type EstudoResumo = {
  id: string; origem: "paciente" | "avulso";
  paciente_id: string | null;
  preview: string; provider: string | null;
  criado_em: string; atualizado_em: string;
};

export default function Page() {
  const router = useRouter();
  const [rows, setRows] = useState<EstudoResumo[]>([]);
  const [loading, setLoading] = useState(true);
  const [openModal, setOpenModal] = useState(false);
  const [confirmId, setConfirmId] = useState<string | null>(null);
  const [removing, setRemoving] = useState(false);

  const carregar = async () => {
    try {
      setRows(await api<EstudoResumo[]>("/supervisao/estudos"));
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) router.replace("/login");
      else toast.error(err instanceof ApiError ? err.message : "Erro");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!getToken()) return void router.replace("/login");
    carregar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [router]);

  async function confirmarRemocao() {
    if (!confirmId) return;
    setRemoving(true);
    try {
      await api(`/supervisao/estudos/${confirmId}`, { method: "DELETE" });
      setRows((r) => r.filter((x) => x.id !== confirmId));
      toast.success("Estudo removido.");
      setConfirmId(null);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Falha");
    } finally {
      setRemoving(false);
    }
  }

  return (
    <>
      <Topbar />
      <main className="container-praxis" style={{ maxWidth: 960 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <h1 style={{ fontSize: "var(--fs-xl)", margin: 0, display: "flex", alignItems: "center", gap: 8 }}>
            <Compass size={20} color="var(--brand-2)" /> Supervisão · Estudo de Caso
          </h1>
          <Button variant="primary" onClick={() => setOpenModal(true)}>
            <PlusCircle size={16} /> Nova análise
          </Button>
        </div>
        <p style={{ color: "var(--muted)", fontSize: 13, marginTop: 6 }}>
          Traga um caso do prontuário ou avulso — o Práxis apresenta leituras por abordagem
          com base no acervo. Apoio formativo; a conduta clínica segue sendo do profissional.
        </p>

        {loading ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 10, marginTop: 12 }}>
            <Skeleton height={64} radius="var(--radius-lg)" />
            <Skeleton height={64} radius="var(--radius-lg)" />
          </div>
        ) : rows.length === 0 ? (
          <div style={{ marginTop: 12 }}>
            <EmptyState
              icone={<Compass size={28} />}
              frase="Nenhum estudo ainda."
              cta={<Button variant="primary" onClick={() => setOpenModal(true)}><PlusCircle size={16} /> Nova análise</Button>}
            />
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 10, marginTop: 12 }}>
            {rows.map((r) => (
              <Card key={r.id} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
                <div style={{ minWidth: 0 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                    <span className="badge">{r.origem === "paciente" ? "prontuário" : "avulso"}</span>
                    {r.paciente_id && (
                      <Link className="link" href={`/pacientes/${r.paciente_id}`} style={{ display: "inline-flex", alignItems: "center", gap: 4, fontSize: 12 }}>
                        <Users2 size={12} /> paciente
                      </Link>
                    )}
                    <span style={{ color: "var(--muted)", fontSize: 12 }}>
                      {new Date(r.criado_em).toLocaleString("pt-BR")}
                    </span>
                  </div>
                  <div style={{ color: "var(--text)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {r.preview || "(sem prévia)"}
                  </div>
                </div>
                <div style={{ display: "flex", gap: 8, flexShrink: 0 }}>
                  <Link href={`/supervisao/${r.id}`} className="btn">Abrir</Link>
                  <Button variant="danger" className="btn-icon" onClick={() => setConfirmId(r.id)} title="Remover" aria-label="Remover">
                    <Trash2 size={14} />
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        )}
      </main>
      {openModal && (
        <SupervisaoModal onClose={() => setOpenModal(false)} onCreated={() => { setOpenModal(false); carregar(); }} />
      )}
      <ConfirmDialog
        open={confirmId !== null}
        title="Remover estudo"
        description="Este estudo de caso será removido permanentemente. Esta ação não pode ser desfeita."
        confirmLabel="Remover estudo"
        busy={removing}
        onConfirm={confirmarRemocao}
        onCancel={() => setConfirmId(null)}
      />
    </>
  );
}
