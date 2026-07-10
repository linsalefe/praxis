"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import { FolderKanban, Users2 } from "lucide-react";
import { api, ApiError, getToken } from "@/lib/api";
import { formatNome } from "@/lib/format";
import { dataRelativa } from "@/lib/date";
import { Topbar } from "@/components/Topbar";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Card } from "@/components/ui/Card";
import { SectionTitle } from "@/components/ui/SectionTitle";
import { Skeleton } from "@/components/ui/Skeleton";
import { EmptyState } from "@/components/ui/EmptyState";

type CasoCompartilhado = {
  id: string; paciente_id: string; paciente_nome: string;
  titulo: string | null; status: string; dono_nome: string | null;
  aberto_em: string; pts_versao_atual: number | null;
};

export default function CasosCompartilhadosPage() {
  const router = useRouter();
  const [casos, setCasos] = useState<CasoCompartilhado[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!getToken()) return void router.replace("/login");
    (async () => {
      try {
        setCasos(await api<CasoCompartilhado[]>("/casos/compartilhados"));
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) router.replace("/login");
        else toast.error(err instanceof ApiError ? err.message : "Falha ao carregar os casos");
      } finally {
        setLoading(false);
      }
    })();
  }, [router]);

  return (
    <>
      <Topbar />
      <main className="container-praxis">
        <SectionTitle margin="0 0 6px">Casos compartilhados</SectionTitle>
        <p style={{ color: "var(--muted)", fontSize: 13, margin: "0 0 16px" }}>
          Casos que a equipe compartilhou para cuidado conjunto — PTS, matriciamento e rede
          construídos a várias mãos. Só o que foi explicitamente compartilhado aparece aqui.
        </p>

        {loading ? (
          <Skeleton />
        ) : casos.length === 0 ? (
          <EmptyState
            icone={<Users2 size={28} />}
            frase="Nenhum caso compartilhado ainda. Abra um caso e ligue “Compartilhar com a equipe” para colaborar nele."
          />
        ) : (
          casos.map((c) => (
            <Card key={c.id} style={{ marginBottom: 8, display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8, flexWrap: "wrap" }}>
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <StatusBadge status={c.status} />
                  <span style={{ fontWeight: 500 }}>{c.titulo || "Caso sem título"}</span>
                </div>
                <div style={{ color: "var(--muted)", fontSize: 12, marginTop: 2 }}>
                  {formatNome(c.paciente_nome)} · aberto {dataRelativa(c.aberto_em)}
                  {c.dono_nome && ` · responsável: ${formatNome(c.dono_nome)}`}
                  {` · PTS ${c.pts_versao_atual ? `v${c.pts_versao_atual}` : "não iniciado"}`}
                </div>
              </div>
              <Link href={`/casos/${c.id}`} className="btn"><FolderKanban size={16} /> Abrir</Link>
            </Card>
          ))
        )}
      </main>
    </>
  );
}
