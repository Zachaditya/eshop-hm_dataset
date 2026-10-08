/** Email-based demo authentication using storefront-scoped session cookies. */
import { SESSION_API_BASE } from "./sessionApi";

/**
 * Send an authentication request through the same-origin backend proxy.
 * @param path Backend authentication endpoint, starting with a slash.
 * @param opts Request method, headers, and optional JSON body.
 * @returns The decoded response, or a rejected promise for an API error.
 */
async function api<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const resp = await fetch(`${SESSION_API_BASE}${path}`, {
    ...opts,
    credentials: "include", // cookie session
    headers: { "Content-Type": "application/json", ...(opts.headers ?? {}) },
    cache: "no-store",
  });

  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`API ${resp.status}: ${text}`);
  }
  return resp.json() as Promise<T>;
}

/**
 * Create a demo account and retain its session cookie on the storefront host.
 * @param input Account email and optional display name.
 * @returns The created account, or a rejected promise containing the API error.
 */
export async function register(input: { email: string; name?: string }) {
  const resp = await fetch(`${SESSION_API_BASE}/auth/register`, {
    method: "POST",
    credentials: "include",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(input),
    cache: "no-store",
  });
  if (!resp.ok) throw new Error(await resp.text());
  return resp.json();
}

/**
 * Read the account identified by the current storefront session cookie.
 * Params: None.
 * @returns The authenticated account, or a rejected promise for an invalid session.
 */
export async function me() {
  const resp = await fetch(`${SESSION_API_BASE}/auth/me`, {
    credentials: "include",
    cache: "no-store",
  });
  if (!resp.ok) throw new Error(await resp.text());
  return resp.json();
}

/**
 * Start a session for an existing email-based demo account.
 * @param input Account email and the current form's unused password field.
 * @returns The account associated with the new storefront session.
 */
export function login(input: { email: string; password: string }) {
  return api<{ id: string; name: string; email: string }>("/auth/login", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

/**
 * End the current backend session and clear its storefront cookie.
 * Params: None.
 * @returns The backend logout acknowledgement.
 */
export function logout() {
  return api<{ ok: boolean }>("/auth/logout", { method: "POST" });
}
