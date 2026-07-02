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
  texto: string | null;   // texto integral da seção; só vem em obras próprias do CENAT
};

type Detalhe = { obra: Obra; indice: IndiceItem[] };

function paginas(pi: number | null, pf: number | null): string {
  if (!pi) return "p. n/d";
  return pf && pf !== pi ? `pp. ${pi}-${pf}` : `p. ${pi}`;
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
  const indice = data?.indice ?? [];
  // Obras próprias do CENAT vêm com texto → leitura; terceiros só estrutura.
  const podeLer = !!obra && !obra.is_terceiro;

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

            <SectionTitle margin="0 0 10px">{podeLer ? "Conteúdo" : "Índice"}</SectionTitle>
            {indice.length === 0 ? (
              <Card>
                <p style={{ margin: 0, color: "var(--muted)" }}>
                  {podeLer ? "Conteúdo indisponível para esta obra." : "Índice indisponível para esta obra."}
                </p>
              </Card>
            ) : podeLer ? (
              // Obra própria do CENAT — leitura corrida das seções, na ordem.
              <div style={{ display: "grid", gap: 16 }}>
                {indice.map((it, i) => (
                  <Card key={it.ordem}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                      <span className="badge">Seção {i + 1}</span>
                      <span className="badge">{paginas(it.pagina_inicio, it.pagina_fim)}</span>
                    </div>
                    <p style={{ margin: 0, whiteSpace: "pre-wrap", lineHeight: 1.65 }}>{it.texto}</p>
                  </Card>
                ))}
              </div>
            ) : (
              // Obra de terceiros — só estrutura navegável por páginas (sem texto).
              <Card style={{ padding: 0 }}>
                {indice.map((it, i) => (
                  <div
                    key={it.ordem}
                    style={{
                      display: "flex", justifyContent: "space-between", gap: 12,
                      padding: "12px 14px",
                      borderTop: i === 0 ? "none" : "1px solid var(--border)",
                    }}
                  >
                    <span>Seção {i + 1}</span>
                    <span style={{ color: "var(--muted)", fontSize: 13, whiteSpace: "nowrap" }}>
                      {paginas(it.pagina_inicio, it.pagina_fim)}
                    </span>
                  </div>
                ))}
              </Card>
            )}
          </>
        ) : null}
      </main>
    </>
  );
}
