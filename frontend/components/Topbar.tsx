"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { Compass, LogOut, ShieldCheck, Sparkles, Users } from "lucide-react";
import { clearToken } from "@/lib/api";

export function Topbar({ meNome }: { meNome?: string }) {
  const router = useRouter();
  function logout() {
    clearToken();
    router.replace("/login");
  }
  return (
    <header
      style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "12px 24px", borderBottom: "1px solid var(--border)",
        background: "var(--surface)",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
        <Link href="/pacientes" className="link" style={{ display: "flex", alignItems: "center", gap: 8, textDecoration: "none", color: "var(--text)" }}>
          <ShieldCheck size={18} color="var(--brand-2)" />
          <strong>Práxis</strong>
          <span className="badge">by CENAT</span>
        </Link>
        <Link href="/pacientes" className="link" style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
          <Users size={16} /> Pacientes
        </Link>
        <Link href="/sofia" className="link" style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
          <Sparkles size={16} /> Sofia
        </Link>
        <Link href="/supervisao" className="link" style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
          <Compass size={16} /> Supervisão
        </Link>
        <Link href="/conta/2fa" className="link">Conta / 2FA</Link>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        {meNome && <span style={{ color: "var(--muted)", fontSize: 13 }}>{meNome}</span>}
        <button className="btn" onClick={logout}>
          <LogOut size={14} /> Sair
        </button>
      </div>
    </header>
  );
}
