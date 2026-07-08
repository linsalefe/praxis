"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter, usePathname } from "next/navigation";
import {
  BookOpen, CalendarDays, ChevronDown, Compass, IdCard, LayoutGrid, LogOut, Menu,
  UserCog, Users, UsersRound, Wallet,
} from "lucide-react";
import { api, clearToken } from "@/lib/api";
import { PresenceMark } from "@/components/ui/PresenceMark";
import { Drawer } from "@/components/ui/Drawer";
import { Button } from "@/components/ui/Button";

type Item = { href: string; label: string; icon: React.ReactNode };

const NAV: Item[] = [
  { href: "/inicio", label: "Início", icon: <LayoutGrid size={16} /> },
  { href: "/agenda", label: "Agenda", icon: <CalendarDays size={16} /> },
  { href: "/pacientes", label: "Pacientes", icon: <Users size={16} /> },
  { href: "/grupos", label: "Grupos", icon: <UsersRound size={16} /> },
  { href: "/sofia", label: "Sofia", icon: <PresenceMark size={16} /> },
  { href: "/biblioteca", label: "Biblioteca", icon: <BookOpen size={16} /> },
  { href: "/financeiro", label: "Financeiro", icon: <Wallet size={16} /> },
  { href: "/supervisao", label: "Supervisão", icon: <Compass size={16} /> },
  { href: "/conta/2fa", label: "Conta / 2FA", icon: <UserCog size={16} /> },
];

// No desktop, "Conta / 2FA" sai da barra inline e vive no menu de conta (G5).
const NAV_INLINE = NAV.filter((it) => it.href !== "/conta/2fa");

function ehAtivo(pathname: string | null, href: string): boolean {
  if (!pathname) return false;
  return pathname === href || pathname.startsWith(href + "/");
}

function iniciais(nome: string): string {
  const p = nome.trim().split(/\s+/).filter(Boolean);
  if (p.length === 0) return "·";
  if (p.length === 1) return p[0].slice(0, 2).toUpperCase();
  return (p[0][0] + p[p.length - 1][0]).toUpperCase();
}

export function Topbar({ meNome }: { meNome?: string }) {
  const router = useRouter();
  const pathname = usePathname();
  const [menu, setMenu] = useState(false);
  const [conta, setConta] = useState(false);
  const [nome, setNome] = useState<string>(meNome ?? "");
  const [papel, setPapel] = useState<string | null>(null);
  const contaRef = useRef<HTMLDivElement>(null);

  // Nome (se não veio por prop) e papel — o papel gate o item "Equipe" (owner).
  useEffect(() => {
    let vivo = true;
    api<{ nome: string; papel: string }>("/auth/me")
      .then((m) => { if (vivo) { if (!meNome) setNome(m.nome); setPapel(m.papel); } })
      .catch(() => { /* menu degrada para rótulo genérico */ });
    return () => { vivo = false; };
  }, [meNome]);

  // Fecha o dropdown ao clicar fora / Esc.
  useEffect(() => {
    if (!conta) return;
    const onDoc = (e: MouseEvent) => {
      if (contaRef.current && !contaRef.current.contains(e.target as Node)) setConta(false);
    };
    const onEsc = (e: KeyboardEvent) => { if (e.key === "Escape") setConta(false); };
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onEsc);
    return () => { document.removeEventListener("mousedown", onDoc); document.removeEventListener("keydown", onEsc); };
  }, [conta]);

  async function logout() {
    try { await api("/auth/logout", { method: "POST" }); } catch { /* revogação best-effort */ }
    clearToken();
    router.replace("/login");
  }

  const rotuloConta = nome || "Minha conta";

  return (
    <header
      style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "12px 24px", borderBottom: "1px solid var(--border)",
        background: "var(--surface)",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 16, minWidth: 0 }}>
        <Link href="/inicio" className="link" style={{ display: "flex", alignItems: "center", gap: 8, textDecoration: "none", color: "var(--text)" }}>
          <span style={{ fontFamily: "var(--font-display)", fontWeight: 600, fontSize: 18, letterSpacing: "-0.01em" }}>
            Práxis<span style={{ color: "var(--amber-600)" }}>.</span>
          </span>
          <span className="badge">by CENAT</span>
        </Link>
        <nav className="topbar-links">
          {NAV_INLINE.map((it) => {
            const ativo = ehAtivo(pathname, it.href);
            return (
              <Link
                key={it.href}
                href={it.href}
                className={`link topbar-link${ativo ? " ativo" : ""}`}
                aria-current={ativo ? "page" : undefined}
                style={{ display: "inline-flex", alignItems: "center", gap: 6 }}
              >
                {it.icon} {it.label}
              </Link>
            );
          })}
        </nav>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        {/* Menu de conta (desktop) — avatar/nome → dropdown */}
        <div className="topbar-links" style={{ position: "relative" }} ref={contaRef}>
          <button
            type="button"
            onClick={() => setConta((v) => !v)}
            aria-haspopup="menu"
            aria-expanded={conta}
            className="btn"
            style={{ display: "inline-flex", alignItems: "center", gap: 8 }}
          >
            <span
              aria-hidden
              style={{
                width: 24, height: 24, borderRadius: "var(--radius-full)",
                background: "var(--teal-100)", color: "var(--teal-700)",
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: 11, fontWeight: 600,
              }}
            >
              {iniciais(rotuloConta)}
            </span>
            <span style={{ maxWidth: 160, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {rotuloConta}
            </span>
            <ChevronDown size={14} />
          </button>
          {conta && (
            <div
              role="menu"
              style={{
                position: "absolute", right: 0, top: "calc(100% + 6px)", minWidth: 200,
                background: "var(--surface)", border: "1px solid var(--border)",
                borderRadius: "var(--radius-md)", boxShadow: "var(--shadow-md)",
                padding: 6, zIndex: "var(--z-nav)",
              }}
            >
              <Link
                href="/conta" role="menuitem" onClick={() => setConta(false)}
                className="link"
                style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 10px", borderRadius: "var(--radius-sm, 6px)", color: "var(--text)" }}
              >
                <IdCard size={15} /> Perfil / timbre
              </Link>
              <Link
                href="/conta/2fa" role="menuitem" onClick={() => setConta(false)}
                className="link"
                style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 10px", borderRadius: "var(--radius-sm, 6px)", color: "var(--text)" }}
              >
                <UserCog size={15} /> Conta / 2FA
              </Link>
              {papel === "owner" && (
                <Link
                  href="/conta/equipe" role="menuitem" onClick={() => setConta(false)}
                  className="link"
                  style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 10px", borderRadius: "var(--radius-sm, 6px)", color: "var(--text)" }}
                >
                  <UsersRound size={15} /> Equipe
                </Link>
              )}
              <button
                type="button" role="menuitem" onClick={() => { setConta(false); logout(); }}
                className="link"
                style={{ display: "flex", width: "100%", alignItems: "center", gap: 8, padding: "8px 10px", borderRadius: "var(--radius-sm, 6px)", background: "none", border: "none", cursor: "pointer", color: "var(--danger)", textAlign: "left" }}
              >
                <LogOut size={15} /> Sair
              </button>
            </div>
          )}
        </div>

        <Button
          className="topbar-burger"
          onClick={() => setMenu(true)}
          aria-label="Abrir menu"
          aria-expanded={menu}
        >
          <Menu size={18} />
        </Button>
      </div>

      <Drawer open={menu} title="Menu" onClose={() => setMenu(false)}>
        <nav style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          {NAV.map((it) => {
            const ativo = ehAtivo(pathname, it.href);
            return (
              <Link
                key={it.href}
                href={it.href}
                onClick={() => setMenu(false)}
                className={`link topbar-link${ativo ? " ativo" : ""}`}
                aria-current={ativo ? "page" : undefined}
                style={{ display: "flex", alignItems: "center", gap: 8, padding: "10px 8px", borderRadius: "var(--radius-md)" }}
              >
                {it.icon} {it.label}
              </Link>
            );
          })}
          {papel === "owner" && (
            <Link
              href="/conta/equipe"
              onClick={() => setMenu(false)}
              className={`link topbar-link${ehAtivo(pathname, "/conta/equipe") ? " ativo" : ""}`}
              aria-current={ehAtivo(pathname, "/conta/equipe") ? "page" : undefined}
              style={{ display: "flex", alignItems: "center", gap: 8, padding: "10px 8px", borderRadius: "var(--radius-md)" }}
            >
              <UsersRound size={16} /> Equipe
            </Link>
          )}
          <hr className="divider" />
          <Button onClick={() => { setMenu(false); logout(); }} style={{ justifyContent: "flex-start" }}>
            <LogOut size={14} /> Sair
          </Button>
        </nav>
      </Drawer>
    </header>
  );
}
