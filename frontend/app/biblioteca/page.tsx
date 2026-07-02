"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { BookOpen, Search } from "lucide-react";
import { api, ApiError, getToken } from "@/lib/api";
import { Topbar } from "@/components/Topbar";
import { PresenceMark } from "@/components/ui/PresenceMark";
import { SkeletonCard } from "@/components/ui/Skeleton";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { SectionTitle } from "@/components/ui/SectionTitle";

type Obra = {
  id: string; slug: string; titulo: string; autor: string;
  editora: string | null; ano: number | null;
  is_terceiro: boolean; total_chunks: number;
};

type Hit = {
  slug: string; titulo: string; capitulo: string | null;
  pagina_inicio: number | null; pagina_fim: number | null;
  trecho: string; is_terceiro: boolean; similaridade: number;
};

function paginas(pi: number | null, pf: number | null): string {
  if (!pi) return "p. n/d";
  return pf && pf !== pi ? `pp. ${pi}-${pf}` : `p. ${pi}`;
}

export default function BibliotecaPage() {
  const router = useRouter();
  const [obras, setObras] = useState<Obra[]>([]);
  const [loading, setLoading] = useState(true);

  const [q, setQ] = useState("");
  const [hits, setHits] = useState<Hit[] | null>(null);
  const [buscando, setBuscando] = useState(false);

  useEffect(() => {
    if (!getToken()) return void router.replace("/login");
    (async () => {
      try { setObras(await api<Obra[]>("/biblioteca")); }
      catch (err) { if (err instanceof ApiError && err.status === 401) router.replace("/login"); }
      finally { setLoading(false); }
    })();
  }, [router]);

  async function buscar(e: React.FormEvent) {
    e.preventDefault();
    const termo = q.trim();
    if (termo.length < 3) return;
    setBuscando(true);
    try {
      setHits(await api<Hit[]>("/biblioteca/buscar", {
        method: "POST", body: JSON.stringify({ q: termo }),
      }));
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) return router.replace("/login");
      setHits([]);
    } finally {
      setBuscando(false);
    }
  }

  function limpar() {
    setQ("");
    setHits(null);
  }

  return (
    <>
      <Topbar />
      <main className="container-praxis" style={{ maxWidth: 980 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
          <PresenceMark size={26} />
          <h1 style={{ margin: 0, fontSize: 22 }}>Biblioteca viva</h1>
          <span className="badge">acervo CENAT</span>
        </div>
        <p style={{ color: "var(--muted)", margin: "0 0 16px", fontSize: 14 }}>
          Navegue as obras do acervo e faça busca semântica no conteúdo. Trechos de obras
          de terceiros aparecem reduzidos, em respeito aos direitos autorais.
        </p>

        <form onSubmit={buscar} style={{ display: "flex", gap: 8, marginBottom: 20 }}>
          <input
            className="input"
            placeholder="Buscar no acervo… (ex.: reunião de rede em Diálogo Aberto)"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            minLength={3}
          />
          <Button variant="primary" type="submit" loading={buscando}>
            <Search size={16} /> {buscando ? "Buscando…" : "Buscar"}
          </Button>
          {hits !== null && (
            <Button type="button" onClick={limpar}>Limpar</Button>
          )}
        </form>

        {/* Resultados de busca */}
        {buscando && (
          <div style={{ display: "grid", gap: 12, marginBottom: 24 }}>
            <SkeletonCard lines={2} />
            <SkeletonCard lines={2} />
          </div>
        )}

        {!buscando && hits !== null && (
          <section style={{ marginBottom: 28 }}>
            <SectionTitle margin="0 0 10px">
              {hits.length > 0
                ? `${hits.length} trecho${hits.length > 1 ? "s" : ""} no acervo`
                : "Resultados"}
            </SectionTitle>
            {hits.length === 0 ? (
              <Card>
                <p style={{ margin: 0, color: "var(--muted)" }}>
                  Nenhum trecho do acervo respondeu a esta busca. Tente outras palavras.
                </p>
              </Card>
            ) : (
              <div style={{ display: "grid", gap: 12 }}>
                {hits.map((h, i) => (
                  <Link
                    key={i}
                    href={`/biblioteca/${h.slug}`}
                    className="card"
                    style={{ textDecoration: "none", color: "inherit", display: "block" }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", marginBottom: 6 }}>
                      <strong>{h.titulo}</strong>
                      <span className="badge">{h.is_terceiro ? "terceiro" : "CENAT"}</span>
                      <span className="badge">cap. {h.capitulo || "n/d"}</span>
                      <span className="badge">{paginas(h.pagina_inicio, h.pagina_fim)}</span>
                    </div>
                    <p style={{ margin: 0, whiteSpace: "pre-wrap" }}>{h.trecho}</p>
                    {h.is_terceiro && (
                      <p style={{ margin: "8px 0 0", fontSize: 12, color: "var(--brand-2)" }}>
                        trecho reduzido — obra de terceiros
                      </p>
                    )}
                  </Link>
                ))}
              </div>
            )}
          </section>
        )}

        {/* Grade das obras */}
        <SectionTitle margin="0 0 10px">Obras</SectionTitle>
        {loading ? (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: 12 }}>
            <SkeletonCard lines={2} />
            <SkeletonCard lines={2} />
            <SkeletonCard lines={2} />
          </div>
        ) : obras.length === 0 ? (
          <Card>
            <p style={{ margin: 0, color: "var(--muted)" }}>O acervo ainda não tem obras indexadas.</p>
          </Card>
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: 12 }}>
            {obras.map((o) => (
              <Link
                key={o.id}
                href={`/biblioteca/${o.slug}`}
                className="card"
                style={{ textDecoration: "none", color: "inherit", display: "flex", flexDirection: "column", gap: 6 }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <BookOpen size={16} color="var(--brand-2)" />
                  <span className="badge">{o.is_terceiro ? "terceiro" : "CENAT"}</span>
                </div>
                <strong style={{ lineHeight: 1.3 }}>{o.titulo}</strong>
                <span style={{ color: "var(--muted)", fontSize: 13 }}>{o.autor}</span>
                <span style={{ color: "var(--muted)", fontSize: 12 }}>
                  {o.editora || "—"}{o.ano ? ` · ${o.ano}` : ""} · {o.total_chunks} trechos
                </span>
              </Link>
            ))}
          </div>
        )}
      </main>
    </>
  );
}
