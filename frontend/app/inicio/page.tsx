"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import { CalendarClock, FileSignature, FileText, ClipboardList, UserPlus, RotateCcw, ArrowRight } from "lucide-react";
import { api, ApiError, getScope, getToken } from "@/lib/api";
import { dataRelativa } from "@/lib/date";
import { modalidadeLabel } from "@/lib/labels";
import { Topbar } from "@/components/Topbar";
import { PresenceMark } from "@/components/ui/PresenceMark";
import { Skeleton } from "@/components/ui/Skeleton";
import { Card } from "@/components/ui/Card";

type SessaoHoje = {
  sessao_id: string; paciente_id: string; paciente_nome: string;
  data: string; modalidade: string; status: string;
};
type EvolucaoRascunho = {
  evolucao_id: string; sessao_id: string; paciente_id: string; paciente_nome: string; criado_em: string;
};
type DocumentoRascunho = {
  documento_id: string; paciente_id: string; paciente_nome: string; tipo: string; finalidade: string; criado_em: string;
};
type InstrumentoPendente = {
  resposta_id: string; paciente_id: string; paciente_nome: string; instrumento_titulo: string; criado_em: string;
};
type Pendencias = {
  sessoes_hoje: SessaoHoje[];
  evolucoes_rascunho: EvolucaoRascunho[];
  documentos_rascunho: DocumentoRascunho[];
  instrumentos_pendentes: InstrumentoPendente[];
  contadores: { sessoes_hoje: number; evolucoes_rascunho: number; documentos_rascunho: number; instrumentos_pendentes: number };
};
type UltimoPaciente = { id: string; nome: string };

const hora = (iso: string) =>
  new Date(iso).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
const dataCurta = (iso: string) => dataRelativa(iso);

function Bloco({
  titulo,
  contador,
  children,
}: {
  titulo: string;
  contador?: number;
  children: React.ReactNode;
}) {
  return (
    <Card as="section" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <h2 style={{ fontSize: 15, margin: 0, display: "flex", alignItems: "baseline", gap: 8 }}>
        {titulo}
        {contador != null && contador > 0 && (
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--warm-500)" }}>· {contador}</span>
        )}
      </h2>
      {children}
    </Card>
  );
}

function ItemLink({ href, onClick, children }: { href: string; onClick?: () => void; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      onClick={onClick}
      className="link"
      style={{
        display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12,
        padding: "10px 12px", borderRadius: "var(--radius-md)", background: "var(--surface-2)",
        color: "var(--text)", textDecoration: "none",
      }}
    >
      <span style={{ minWidth: 0, display: "flex", alignItems: "center", gap: 10 }}>{children}</span>
      <ArrowRight size={15} color="var(--brand-2)" style={{ flex: "none" }} />
    </Link>
  );
}

const Vazio = ({ children }: { children: React.ReactNode }) => (
  <p style={{ color: "var(--muted)", fontSize: 13, margin: 0 }}>{children}</p>
);

export default function InicioPage() {
  const router = useRouter();
  const [me, setMe] = useState<string | undefined>();
  const [dados, setDados] = useState<Pendencias | null>(null);
  const [loading, setLoading] = useState(true);
  const [ultimo, setUltimo] = useState<UltimoPaciente | null>(null);

  useEffect(() => {
    const t = getToken();
    if (!t) return void router.replace("/login");
    if (getScope() === "pre_2fa") return void router.replace("/login/2fa");

    try {
      const raw = localStorage.getItem("praxis.last_paciente");
      if (raw) setUltimo(JSON.parse(raw));
    } catch { /* ignora */ }

    (async () => {
      try {
        const [meResp, pend] = await Promise.all([
          api<{ nome: string }>("/auth/me"),
          api<Pendencias>("/inicio/pendencias"),
        ]);
        setMe(meResp.nome);
        setDados(pend);
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) router.replace("/login");
        else toast.error(err instanceof ApiError ? err.message : "Falha ao carregar o início");
      } finally {
        setLoading(false);
      }
    })();
  }, [router]);

  const hoje = new Date().toLocaleDateString("pt-BR", { weekday: "long", day: "numeric", month: "long" });
  const c = dados?.contadores;
  const tudoEmDia = c && c.sessoes_hoje + c.evolucoes_rascunho + c.documentos_rascunho + c.instrumentos_pendentes === 0;

  return (
    <>
      <Topbar meNome={me} />
      <main className="container-praxis">
        <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 12, marginBottom: 20 }}>
          <h1 style={{ fontSize: 26, margin: 0 }}>Hoje</h1>
          <span style={{ color: "var(--muted)", fontSize: 14, textTransform: "capitalize" }}>{hoje}</span>
        </div>

        {loading ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <Card style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <Skeleton width="30%" height={14} />
              <Skeleton height={40} /><Skeleton height={40} />
            </Card>
            <div style={{ display: "grid", gap: 16, gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))" }}>
              <Card style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                <Skeleton width="50%" height={14} /><Skeleton height={36} /><Skeleton height={36} />
              </Card>
              <Card style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                <Skeleton width="50%" height={14} /><Skeleton height={36} />
              </Card>
            </div>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {/* Sessões de hoje */}
            <Bloco titulo="Sessões de hoje" contador={c?.sessoes_hoje}>
              {dados && dados.sessoes_hoje.length > 0 ? (
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {dados.sessoes_hoje.map((s) => (
                    <ItemLink key={s.sessao_id} href={`/pacientes/${s.paciente_id}`}>
                      <CalendarClock size={16} color="var(--brand-2)" style={{ flex: "none" }} />
                      <span style={{ fontFamily: "var(--font-mono)", color: "var(--text)" }}>{hora(s.data)}</span>
                      <strong style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{s.paciente_nome}</strong>
                      <span className="badge badge-neutral">{modalidadeLabel(s.modalidade)}</span>
                    </ItemLink>
                  ))}
                </div>
              ) : (
                <Vazio>Nenhuma sessão agendada para hoje.</Vazio>
              )}
            </Bloco>

            {tudoEmDia && (
              <Card style={{ textAlign: "center", padding: 28 }}>
                <p style={{ margin: "0 0 4px", fontFamily: "var(--font-display)", fontSize: 18 }}>Tudo em dia.</p>
                <p style={{ margin: 0, color: "var(--muted)", fontSize: 14 }}>Nenhuma pendência aguardando você.</p>
              </Card>
            )}

            {/* Pendências acionáveis */}
            <div style={{ display: "grid", gap: 16, gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))" }}>
              <Bloco titulo="Aguardando sua assinatura" contador={c?.evolucoes_rascunho}>
                {dados && dados.evolucoes_rascunho.length > 0 ? (
                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    {dados.evolucoes_rascunho.map((e) => (
                      <ItemLink key={e.evolucao_id} href={`/evolucoes/${e.evolucao_id}`}>
                        <FileSignature size={16} color="var(--brand-2)" style={{ flex: "none" }} />
                        <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          Evolução — {e.paciente_nome}
                        </span>
                        <span style={{ color: "var(--muted)", fontSize: 12, flex: "none" }}>{dataCurta(e.criado_em)}</span>
                      </ItemLink>
                    ))}
                  </div>
                ) : (
                  <Vazio>Nenhuma evolução aguardando assinatura.</Vazio>
                )}
              </Bloco>

              <Bloco titulo="Documentos em rascunho" contador={c?.documentos_rascunho}>
                {dados && dados.documentos_rascunho.length > 0 ? (
                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    {dados.documentos_rascunho.map((d) => (
                      <ItemLink key={d.documento_id} href={`/documentos/${d.documento_id}`}>
                        <FileText size={16} color="var(--brand-2)" style={{ flex: "none" }} />
                        <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", textTransform: "capitalize" }}>
                          {d.tipo} — {d.paciente_nome}
                        </span>
                      </ItemLink>
                    ))}
                  </div>
                ) : (
                  <Vazio>Nenhum documento em rascunho.</Vazio>
                )}
              </Bloco>

              <Bloco titulo="Instrumentos para interpretar" contador={c?.instrumentos_pendentes}>
                {dados && dados.instrumentos_pendentes.length > 0 ? (
                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    {dados.instrumentos_pendentes.map((r) => (
                      <ItemLink key={r.resposta_id} href={`/instrumentos/${r.resposta_id}`}>
                        <ClipboardList size={16} color="var(--brand-2)" style={{ flex: "none" }} />
                        <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          {r.instrumento_titulo} — {r.paciente_nome}
                        </span>
                      </ItemLink>
                    ))}
                  </div>
                ) : (
                  <Vazio>Nenhum instrumento aguardando interpretação.</Vazio>
                )}
              </Bloco>
            </div>

            {/* Retomar */}
            {ultimo && (
              <Bloco titulo="Retomar">
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  <ItemLink href={`/pacientes/${ultimo.id}`}>
                    <RotateCcw size={16} color="var(--brand-2)" style={{ flex: "none" }} />
                    <span>Último paciente aberto: <strong>{ultimo.nome}</strong></span>
                  </ItemLink>
                  <ItemLink href={`/sofia?paciente_id=${ultimo.id}`}>
                    <PresenceMark size={16} />
                    <span>Perguntar à Sofia sobre este caso</span>
                  </ItemLink>
                </div>
              </Bloco>
            )}

            {/* Ações rápidas */}
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <Link href="/pacientes?novo=1" className="btn btn-primary">
                <UserPlus size={16} /> Novo paciente
              </Link>
              <Link href="/sofia" className="btn">
                <PresenceMark size={16} /> Perguntar à Sofia
              </Link>
            </div>
          </div>
        )}
      </main>
    </>
  );
}
