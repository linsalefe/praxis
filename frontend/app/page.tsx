"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { getToken, getScope } from "@/lib/api";

export default function Home() {
  const router = useRouter();
  useEffect(() => {
    const tok = getToken();
    const scope = getScope();
    if (!tok) router.replace("/login");
    else if (scope === "pre_2fa") router.replace("/login/2fa");
    else router.replace("/pacientes");
  }, [router]);
  return (
    <main className="container-praxis">
      <p style={{ color: "var(--muted)" }}>Carregando…</p>
    </main>
  );
}
