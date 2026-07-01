"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import { Compass, PlusCircle, Trash2, Users2 } from "lucide-react";
import { api, ApiError, getToken } from "@/lib/api";
import { Topbar } from "@/components/Topbar";
import { SupervisaoModal } from "@/components/SupervisaoModal";

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

  async function remover(id: string) {
    if (!confirm("Remover este estudo?")) return;
    try {
      await api(`/supervisao/estudos/${id}`, { method: "DELETE" });
      setRows((r) => r.filter((x) => x.id !== id));
      toast.success("Removido.");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Falha");
    }
  }

  return (
    <>
      <Topbar />
      <main className="container-praxis" style={{ maxWidth: 960 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <h1 style={{ fontSize: 22, margin: 0, display: "flex", alignItems: "center", gap: 8 }}>
            <Compass size={20} color="var(--brand-2)" /> Supervisão · Estudo de Caso
          </h1>
          <button className="btn btn-primary" onClick={() => setOpenModal(true)}>
            <PlusCircle size={16} /> Nova análise
          </button>
        </div>
        <p style={{ color: "var(--muted)", fontSize: 13, marginTop: 6 }}>
          Traga um caso do prontuário ou avulso — o Práxis apresenta leituras por abordagem
          com base no acervo. Apoio formativo; a conduta clínica segue sendo do profissional.
        </p>

        {loading ? (
          <p style={{ color: "var(--muted)" }}>Carregando…</p>
        ) : rows.length === 0 ? (
          <p style={{ color: "var(--muted)" }}>Nenhum estudo ainda. Crie o primeiro em "Nova análise".</p>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 10, marginTop: 12 }}>
            {rows.map((r) => (
              <div key={r.id} className="card" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
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
                  <button className="btn btn-danger" onClick={() => remover(r.id)} title="Remover">
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
      {openModal && (
        <SupervisaoModal onClose={() => setOpenModal(false)} onCreated={() => { setOpenModal(false); carregar(); }} />
      )}
    </>
  );
}
