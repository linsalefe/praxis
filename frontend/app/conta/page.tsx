"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { IdCard, Save } from "lucide-react";
import { api, ApiError, getToken } from "@/lib/api";
import { Topbar } from "@/components/Topbar";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { Field } from "@/components/ui/Field";

type Me = {
  id: string; nome: string; email: string; crp: string | null;
  crp_verificado: boolean;
  nome_exibicao: string | null;
  registro_profissional: string | null;
  contato_timbre: string | null;
};

export default function ContaPerfil() {
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);
  const [nomeExibicao, setNomeExibicao] = useState("");
  const [registro, setRegistro] = useState("");
  const [contato, setContato] = useState("");
  const [salvando, setSalvando] = useState(false);

  useEffect(() => {
    if (!getToken()) return void router.replace("/login");
    (async () => {
      try {
        const m = await api<Me>("/auth/me");
        setMe(m);
        setNomeExibicao(m.nome_exibicao ?? "");
        setRegistro(m.registro_profissional ?? "");
        setContato(m.contato_timbre ?? "");
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) router.replace("/login");
      }
    })();
  }, [router]);

  async function salvar(e: React.FormEvent) {
    e.preventDefault();
    setSalvando(true);
    try {
      const m = await api<Me>("/auth/me", {
        method: "PATCH",
        body: JSON.stringify({
          nome_exibicao: nomeExibicao,
          registro_profissional: registro,
          contato_timbre: contato,
        }),
      });
      setMe(m);
      setNomeExibicao(m.nome_exibicao ?? "");
      setRegistro(m.registro_profissional ?? "");
      setContato(m.contato_timbre ?? "");
      toast.success("Timbre atualizado.");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Não foi possível salvar.");
    } finally {
      setSalvando(false);
    }
  }

  if (!me) return (
    <>
      <Topbar />
      <main className="container-praxis" style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <Skeleton height={28} width="40%" />
        <Skeleton height={140} radius="var(--radius-lg)" />
      </main>
    </>
  );

  return (
    <>
      <Topbar meNome={me.nome} />
      <main className="container-praxis" style={{ maxWidth: 560 }}>
        <h1 style={{ fontSize: "var(--fs-xl)", margin: "8px 0 6px", display: "flex", alignItems: "center", gap: 8 }}>
          <IdCard size={20} /> Timbre profissional
        </h1>
        <p style={{ color: "var(--muted)", marginTop: 0 }}>
          Aparece no cabeçalho dos documentos gerados (recibos, documentos, anexos de instrumento).
          Todos os campos são opcionais — em branco, usamos seu nome e registro cadastrados.
        </p>
        <Card>
          <form onSubmit={salvar} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <Field label="Nome de exibição">
              <input
                className="input"
                value={nomeExibicao}
                maxLength={160}
                placeholder={me.nome}
                onChange={(e) => setNomeExibicao(e.target.value)}
              />
            </Field>
            <Field label="Registro profissional">
              <input
                className="input"
                value={registro}
                maxLength={64}
                placeholder={me.crp ?? "ex.: CRP 06/12345"}
                onChange={(e) => setRegistro(e.target.value)}
              />
              {me.crp && !me.crp_verificado && (
                <p style={{ margin: "6px 0 0", fontSize: 12, color: "var(--muted)" }}>
                  CRP {me.crp} — verificação pendente.
                </p>
              )}
            </Field>
            <Field label="Contato no timbre">
              <input
                className="input"
                value={contato}
                maxLength={255}
                placeholder="ex.: atendimento@exemplo.com · (11) 90000-0000"
                onChange={(e) => setContato(e.target.value)}
              />
            </Field>
            <div>
              <Button variant="primary" type="submit" disabled={salvando}>
                <Save size={16} /> {salvando ? "Salvando…" : "Salvar timbre"}
              </Button>
            </div>
          </form>
        </Card>
      </main>
    </>
  );
}
