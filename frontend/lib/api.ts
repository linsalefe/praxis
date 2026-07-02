/** Cliente HTTP fino com JWT em localStorage. */
const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8040";

const TOKEN_KEY = "praxis.token";
const TOKEN_SCOPE_KEY = "praxis.token.scope";

export function saveToken(token: string, scope: string = "session"): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(TOKEN_SCOPE_KEY, scope);
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function getScope(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_SCOPE_KEY);
}

export function clearToken(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(TOKEN_SCOPE_KEY);
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export async function api<T = unknown>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init.headers as Record<string, string> | undefined),
  };
  const tok = getToken();
  if (tok) headers.Authorization = `Bearer ${tok}`;

  const res = await fetch(`${API_BASE}${path}`, { ...init, headers });

  // Interceptor global de sessão expirada: 401 ⇒ limpa token e manda ao login.
  // Cobre todas as chamadas via api(). Evita loop na própria rota de login.
  if (res.status === 401 && typeof window !== "undefined") {
    const emLogin = window.location.pathname.startsWith("/login");
    clearToken();
    if (!emLogin) {
      handle401();
      throw new ApiError(401, "Sessão expirada");
    }
  }

  const text = await res.text();
  const data = text ? JSON.parse(text) : null;
  if (!res.ok) {
    const detail = (data && (data.detail || data.message)) || res.statusText;
    throw new ApiError(res.status, typeof detail === "string" ? detail : JSON.stringify(detail));
  }

  // Sliding session: após qualquer chamada autenticada bem-sucedida, se o token
  // está perto de expirar, renova em background (sem bloquear a resposta atual).
  if (path !== "/auth/renovar") void maybeRenovarSessao();

  return data as T;
}

let _handling401 = false;

// --- Renovação silenciosa de sessão (sliding session) -----------------------
let _renewing = false;
// Dispara a ≤10min do exp — dentro da janela de 15min do backend, sem provocar
// rajada de 204 (backend só renova dentro dela; fora, responde no-op).
const JANELA_CLIENTE_S = 10 * 60;

/** Segundos até o exp do JWT (decodifica o payload localmente), ou null. */
function tokenExpiraEmSegundos(token: string): number | null {
  try {
    const payloadB64 = token.split(".")[1];
    if (!payloadB64) return null;
    const json = JSON.parse(atob(payloadB64.replace(/-/g, "+").replace(/_/g, "/")));
    if (typeof json.exp !== "number") return null;
    return json.exp - Math.floor(Date.now() / 1000);
  } catch {
    return null;
  }
}

async function maybeRenovarSessao(): Promise<void> {
  if (_renewing || typeof window === "undefined") return;
  const tok = getToken();
  if (!tok || getScope() !== "session") return;
  const restante = tokenExpiraEmSegundos(tok);
  if (restante === null || restante > JANELA_CLIENTE_S) return;
  _renewing = true;
  try {
    const r = await api<{ access_token?: string } | null>("/auth/renovar", { method: "POST" });
    if (r && r.access_token) saveToken(r.access_token, "session");
    // 204 (fora da janela / teto / token legado) ⇒ r é null: mantém o atual.
  } catch {
    // Silencioso: se a renovação falhar, o fluxo normal de 401 trata a expiração.
  } finally {
    _renewing = false;
  }
}

/** Aviso + redirect uma única vez (evita toasts/redirects em rajada). */
function handle401(): void {
  if (_handling401) return;
  _handling401 = true;
  import("sonner")
    .then((m) => m.toast.error("Sessão expirada, entre novamente."))
    .catch(() => {});
  window.location.assign("/login?expirada=1");
}
