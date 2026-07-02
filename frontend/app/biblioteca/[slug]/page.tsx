"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import Link from "next/link";
import { Info } from "lucide-react";
import { api, ApiError, getToken } from "@/lib/api";
import { Topbar } from "@/components/Topbar";
import { Skeleton, SkeletonCard } from "@/components/ui/Skeleton";
import { Card } from "@/components/ui/Card";
import { SectionTitle } from "@/components/ui/SectionTitle";

type Obra = {
  id: string; slug: string; titulo: string; autor: string;
  editora: string | null; ano: number | null;
  is_terceiro: boolean; total_chunks: number;
};

type IndiceItem = {
  ordem: number; capitulo: string | null; secao_titulo: string | null;
  pagina_inicio: number | null; pagina_fim: number | null;
};

type Detalhe = { obra: Obra; indice: IndiceItem[] };

function paginas(pi: number | null, pf: number | null): string {
  if (!pi) return "p. n/d";
  return pf && pf !== pi ? `pp. ${pi}-${pf}` : `p. ${pi}`;
}

// Agrupa o índice por capítulo, preservando a ordem original.
function agrupar(indice: IndiceItem[]) {
  const grupos: { capitulo: string | null; itens: IndiceItem[] }[] = [];
  for (const it of indice) {
    const ultimo = grupos[grupos.length - 1];
    if (ultimo && ultimo.capitulo === it.capitulo) ultimo.itens.push(it);
    else grupos.push({ capitulo: it.capitulo, itens: [it] });
  }
  return grupos;
}

export default function ObraPage() {
  const router = useRouter();
  const params = useParams<{ slug: string }>();
  const slug = params.slug;

  const [data, setData] = useState<Detalhe | null>(null);
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    if (!getToken()) return void router.replace("/login");
    (async () => {
      try {
        setData(await api<Detalhe>(`/biblioteca/${slug}`));
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) return router.replace("/login");
        setErro(err instanceof ApiError && err.status === 404
          ? "Obra não encontrada no acervo."
          : "Não foi possível carregar esta obra.");
      } finally {
        setLoading(false);
      }
    })();
  }, [router, slug]);

  const obra = data?.obra;
  const grupos = data ? agrupar(data.indice) : [];

  return (
    <>
      <Topbar />
      <main className="container-praxis" style={{ maxWidth: 860 }}>
        <p style={{ margin: 0 }}>
          <Link className="link" href="/biblioteca">← Biblioteca</Link>
        </p>

        {loading ? (
          <div style={{ marginTop: 12, display: "grid", gap: 12 }}>
            <Skeleton width="60%" height={24} />
            <Skeleton width="40%" height={14} />
            <SkeletonCard lines={4} />
          </div>
        ) : erro ? (
          <Card style={{ marginTop: 12 }}>
            <p style={{ margin: 0, color: "var(--muted)" }}>{erro}</p>
          </Card>
        ) : obra ? (
          <>
            <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", margin: "10px 0 4px" }}>
              <h1 style={{ fontSize: 22, margin: 0 }}>{obra.titulo}</h1>
              <span className="badge">{obra.is_terceiro ? "terceiro" : "CENAT"}</span>
            </div>
            <p style={{ color: "var(--muted)", margin: "0 0 14px", fontSize: 14 }}>
              {obra.autor}
              {obra.editora ? ` · ${obra.editora}` : ""}
              {obra.ano ? ` · ${obra.ano}` : ""}
              {` · ${obra.total_chunks} trechos`}
            </p>

            {obra.is_terceiro && (
              <Card
                style={{ display: "flex", gap: 8, alignItems: "flex-start", marginBottom: 16, borderColor: "var(--brand-2)" }}
              >
                <Info size={16} color="var(--brand-2)" style={{ flexShrink: 0, marginTop: 2 }} />
                <p style={{ margin: 0, fontSize: 13, color: "var(--muted)" }}>
                  Obra de terceiros — exibimos apenas a estrutura (capítulos e páginas).
                  Para consultar o conteúdo, use a busca semântica: os trechos vêm reduzidos,
                  em respeito aos direitos autorais.
                </p>
              </Card>
            )}

            <SectionTitle margin="0 0 10px">Índice</SectionTitle>
            {grupos.length === 0 ? (
              <Card>
                <p style={{ margin: 0, color: "var(--muted)" }}>
                  Índice indisponível para esta obra.
                </p>
              </Card>
            ) : (
              <Card style={{ padding: 0 }}>
                {grupos.map((g, gi) => {
                  const pi = g.itens[0].pagina_inicio;
                  const pf = g.itens[g.itens.length - 1].pagina_fim;
                  return (
                    <div
                      key={gi}
                      style={{
                        display: "flex", justifyContent: "space-between", gap: 12,
                        padding: "12px 14px",
                        borderTop: gi === 0 ? "none" : "1px solid var(--border)",
                      }}
                    >
                      <span>
                        {g.capitulo || <span style={{ color: "var(--muted)" }}>Trecho sem capítulo</span>}
                        {g.itens.length > 1 && (
                          <span style={{ color: "var(--muted)", fontSize: 12 }}> · {g.itens.length} partes</span>
                        )}
                      </span>
                      <span style={{ color: "var(--muted)", fontSize: 13, whiteSpace: "nowrap" }}>
                        {paginas(pi, pf)}
                      </span>
                    </div>
                  );
                })}
              </Card>
            )}
          </>
        ) : null}
      </main>
    </>
  );
}
