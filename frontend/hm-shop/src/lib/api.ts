import type { Event, Product, Recommendation } from "./types";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(path, {
    ...init,
    credentials: "include",
    headers: {
      ...(init?.headers || {}),
    },
    cache: "no-store",
  });

  if (!resp.ok) {
    const text = await resp.text().catch(() => "");
    throw new Error(`API error ${resp.status}: ${text}`);
  }

  return resp.json() as Promise<T>;
}

function backendUrl(path: string) {
  // path like "/auth/me" or "/products"
  return `${API_BASE}${path.startsWith("/") ? path : `/${path}`}`;
}

function backendFetch<T>(path: string, init?: RequestInit) {
  return apiFetch<T>(backendUrl(path), init);
}

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

/**
 * Resolves a product image URL.
 * Handles:
 *   - Full https URLs (returned as-is)
 *   - Storage keys like "images_data/011/0110065002.jpg" (rewritten to /images/...)
 *   - Relative paths (prefixed with API_BASE)
 *   - Empty/null (returns "/placeholder.png")
 */
export function resolveImageUrl(imageUrl: string | null | undefined): string {
  const base = API_BASE.replace(/\/$/, "");
  const raw = (imageUrl ?? "").trim();

  if (!raw) return "/placeholder.png";
  if (/^https?:\/\//i.test(raw)) return raw;

  const path = raw.replace(/^\/+/, "");
  const finalPath = path.startsWith("images_data/")
    ? `images/${path.slice("images_data/".length)}`
    : path;

  return `${base}/${finalPath}`;
}

// General product fetching with filters, pagination, search, etc.
export async function getProducts(params?: {
  limit?: number;
  offset?: number;
  q?: string;

  index_group_name?: string[];      
  product_group_name?: string[];    
}) {
  const qs = new URLSearchParams();

  if (params?.limit) qs.set("limit", String(params.limit));
  if (params?.offset) qs.set("offset", String(params.offset));
  if (params?.q) qs.set("q", params.q);

  // IMPORTANT: use append() for list query params
  for (const ig of params?.index_group_name ?? []) qs.append("index_group_name", ig);
  for (const pg of params?.product_group_name ?? []) qs.append("product_group_name", pg);

  return backendFetch<{
    items: Product[];
    total: number;
    limit: number;
    offset: number;
  }>(`/products?${qs.toString()}`);
}

export async function getProduct(id: string) {
  return backendFetch<Product>(`/products/${encodeURIComponent(id)}`);
}

// Below is to fetch products for the homepage
export async function getHomepageProducts(opts: {
  limit?: number;
  group?: string;
  mode?: "men" | "women";
  seed?: number;
}) {
  const qs = new URLSearchParams();
  qs.set("limit", String(opts.limit ?? 12));
  qs.set("group", opts.group ?? "Garment Upper body");
  if (opts.mode) qs.set("mode", opts.mode);
  if (opts.seed !== undefined) qs.set("seed", String(opts.seed));
  return backendFetch<{ items: Product[] }>(`/products/homepage?${qs.toString()}`);
}


export function getEvents() {
  return apiFetch<Event[]>(`/api/events`);
}

export function getRecommendations(productId: string | number) {
  return apiFetch<Recommendation[]>(`/api/recommendations?productId=${encodeURIComponent(String(productId))}`);
}

export function agentChat(payload: unknown) {
  return apiFetch<{ reply: string }>(`/api/agent`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function getSimilarProducts(id: string, params?: { limit?: number; seed?: number }) {
  const qs = new URLSearchParams();
  qs.set("limit", String(params?.limit ?? 8));
  if (params?.seed !== undefined) qs.set("seed", String(params.seed));

  return backendFetch<{ items: Product[] }>(
    `/products/${encodeURIComponent(id)}/similar?${qs.toString()}`
  );
}


