"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { BookOpen } from "lucide-react";
import { api, ApiError, getToken } from "@/lib/api";
import { Topbar } from "@/components/Topbar";
import { Card } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";

type Doc = {
  id: string; slug: string; titulo: string; autor: string;
  editora: string | null; ano: number | null;
  is_terceiro: boolean; total_chunks: number;
};

export default function AcervoPage() {
  const router = useRouter();
  const [rows, setRows] = useState<Doc[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!getToken()) return void router.replace("/login");
    (async () => {
      try { setRows(await api<Doc[]>("/sofia/acervo")); }
      catch (err) { if (err instanceof ApiError && err.status === 401) router.replace("/login"); }
      finally { setLoading(false); }
    })();
  }, [router]);

  return (
    <>
      <Topbar />
      <main className="container-praxis">
        <p style={{ margin: 0 }}><Link className="link" href="/sofia">← Sofia</Link></p>
        <h1 style={{ fontSize: "var(--fs-xl)", margin: "8px 0" }}>
          <BookOpen size={18} style={{ display: "inline", verticalAlign: "middle", marginRight: 6 }} />
          Acervo indexado
        </h1>
        {loading ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <Skeleton height={40} radius="var(--radius-lg)" />
            <Skeleton height={40} radius="var(--radius-lg)" />
            <Skeleton height={40} radius="var(--radius-lg)" />
          </div>
        ) : (
          <Card style={{ padding: 0 }}>
            <table className="table-cards" style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ textAlign: "left", color: "var(--muted)", fontSize: 12 }}>
                  <th style={{ padding: 12 }}>Título</th>
                  <th style={{ padding: 12 }}>Autor</th>
                  <th style={{ padding: 12 }}>Editora</th>
                  <th style={{ padding: 12 }}>Trechos</th>
                  <th style={{ padding: 12 }}>Origem</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((d) => (
                  <tr key={d.id} style={{ borderTop: "1px solid var(--border)" }}>
                    <td data-label="Título" style={{ padding: 12 }}>{d.titulo}</td>
                    <td data-label="Autor" style={{ padding: 12, color: "var(--muted)" }}>{d.autor}</td>
                    <td data-label="Editora" style={{ padding: 12, color: "var(--muted)" }}>{d.editora || "—"}</td>
                    <td data-label="Trechos" style={{ padding: 12 }}>{d.total_chunks}</td>
                    <td data-label="Origem" style={{ padding: 12 }}>
                      <span className="badge">{d.is_terceiro ? "terceiro" : "CENAT"}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        )}
      </main>
    </>
  );
}
