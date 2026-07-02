"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter, usePathname } from "next/navigation";
import {
  BookOpen, CalendarDays, Compass, LayoutGrid, LogOut, Menu,
  ShieldCheck, UserCog, Users, Wallet,
} from "lucide-react";
import { clearToken } from "@/lib/api";
import { PresenceMark } from "@/components/ui/PresenceMark";
import { Drawer } from "@/components/ui/Drawer";
import { Button } from "@/components/ui/Button";

type Item = { href: string; label: string; icon: React.ReactNode };

const NAV: Item[] = [
  { href: "/inicio", label: "Início", icon: <LayoutGrid size={16} /> },
  { href: "/agenda", label: "Agenda", icon: <CalendarDays size={16} /> },
  { href: "/pacientes", label: "Pacientes", icon: <Users size={16} /> },
  { href: "/sofia", label: "Sofia", icon: <PresenceMark size={16} /> },
  { href: "/biblioteca", label: "Biblioteca", icon: <BookOpen size={16} /> },
  { href: "/financeiro", label: "Financeiro", icon: <Wallet size={16} /> },
  { href: "/supervisao", label: "Supervisão", icon: <Compass size={16} /> },
  { href: "/conta/2fa", label: "Conta / 2FA", icon: <UserCog size={16} /> },
];

function ehAtivo(pathname: string | null, href: string): boolean {
  if (!pathname) return false;
  return pathname === href || pathname.startsWith(href + "/");
}

export function Topbar({ meNome }: { meNome?: string }) {
  const router = useRouter();
  const pathname = usePathname();
  const [menu, setMenu] = useState(false);

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
      <div style={{ display: "flex", alignItems: "center", gap: 16, minWidth: 0 }}>
        <Link href="/pacientes" className="link" style={{ display: "flex", alignItems: "center", gap: 8, textDecoration: "none", color: "var(--text)" }}>
          <ShieldCheck size={18} color="var(--brand-2)" />
          <strong>Práxis</strong>
          <span className="badge">by CENAT</span>
        </Link>
        <nav className="topbar-links">
          {NAV.map((it) => {
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
        {meNome && <span style={{ color: "var(--muted)", fontSize: 13 }}>{meNome}</span>}
        <Button className="topbar-links" onClick={logout}>
          <LogOut size={14} /> Sair
        </Button>
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
          <hr className="divider" />
          <Button onClick={() => { setMenu(false); logout(); }} style={{ justifyContent: "flex-start" }}>
            <LogOut size={14} /> Sair
          </Button>
        </nav>
      </Drawer>
    </header>
  );
}
