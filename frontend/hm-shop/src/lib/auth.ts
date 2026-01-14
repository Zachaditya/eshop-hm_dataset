const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

async function api<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`, {
    ...opts,
    credentials: "include", // cookie session
    headers: { "Content-Type": "application/json", ...(opts.headers ?? {}) },
  });

  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`API ${resp.status}: ${text}`);
  }
  return resp.json() as Promise<T>;
}

export async function register(input: { email: string; name?: string }) {
  const resp = await fetch(`${API_BASE}/auth/register`, {
    method: "POST",
    credentials: "include",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(input),
    cache: "no-store",
  });
  if (!resp.ok) throw new Error(await resp.text());
  return resp.json();
}

export async function me() {
  const resp = await fetch(`${API_BASE}/auth/me`, {
    credentials: "include",
    cache: "no-store",
  });
  if (!resp.ok) throw new Error(await resp.text());
  return resp.json();
}

export function login(input: { email: string; password: string }) {
  return api<{ id: string; name: string; email: string }>("/auth/login", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function logout() {
  return api<{ ok: boolean }>("/auth/logout", { method: "POST" });
}

