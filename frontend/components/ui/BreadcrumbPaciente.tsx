"use client";

/**
 * BreadcrumbPaciente (UX-2 U17) — "← Nome do paciente" no topo das páginas de
 * detalhe (documento, instrumento, evolução, supervisão), voltando ao paciente
 * correto sem depender do back do navegador.
 *
 * Resolução do nome (frontend-only): usa o cache `praxis.last_paciente` que a
 * ficha grava; se não bater com o pacienteId, busca `/pacientes/:id`. Quando
 * não há pacienteId (ex.: estudo de supervisão sem paciente), cai no fallback.
 */
import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";

type LastPaciente = { id: string; nome: string };

function lerCache(): LastPaciente | null {
  try {
    const raw = localStorage.getItem("praxis.last_paciente");
    return raw ? (JSON.parse(raw) as LastPaciente) : null;
  } catch {
    return null;
  }
}

export function BreadcrumbPaciente({
  pacienteId,
  fallbackHref = "/pacientes",
  fallbackLabel = "Pacientes",
}: {
  pacienteId?: string | null;
  fallbackHref?: string;
  fallbackLabel?: string;
}) {
  const [nome, setNome] = useState<string | null>(null);

  useEffect(() => {
    if (!pacienteId) return;
    const cache = lerCache();
    if (cache && cache.id === pacienteId) {
      setNome(cache.nome);
      return;
    }
    let vivo = true;
    api<{ id: string; nome: string }>(`/pacientes/${pacienteId}`)
      .then((p) => {
        if (!vivo) return;
        setNome(p.nome);
        try {
          localStorage.setItem("praxis.last_paciente", JSON.stringify({ id: p.id, nome: p.nome }));
        } catch { /* ignora */ }
      })
      .catch(() => { /* mantém rótulo genérico */ });
    return () => { vivo = false; };
  }, [pacienteId]);

  const href = pacienteId ? `/pacientes/${pacienteId}` : fallbackHref;
  const label = pacienteId ? (nome ?? "Paciente") : fallbackLabel;

  return (
    <p style={{ margin: "0 0 12px" }}>
      <Link className="link" href={href}>← {label}</Link>
    </p>
  );
}
