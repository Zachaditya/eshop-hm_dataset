"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";

type Mode = "men" | "women";

type Product = {
  id: string | number;
  name: string;
  price: number;
  image_url: string; // may be full https URL (AWS) or local /images/...
};

function formatUSD(n: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(n);
}

/**
 * Maps your navbar category slug -> allowed product_group_name values.
 * Used only when user searches while inside a category.
 */
const CATEGORY_GROUPS: Record<string, string[]> = {
  clothing: [
    "Garment Upper body",
    "Garment Lower body",
    "Garment Full body",
    "Underwear",
    "Socks & Tights",
    "Swimwear",
    "Nightwear",
  ],
  footwear: ["Shoes"],
  accessories: ["Accessories", "Bags"],
  lifestyle: ["Items", "Furniture", "Stationery", "Garment and Shoe care"],
  other: [],
};

export default function SearchResultsPage() {
  const API_BASE = useMemo(
    () => process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000",
    []
  );

  const sp = useSearchParams();

  const q = (sp.get("q") ?? "").trim();
  const modeParam = (sp.get("mode") ?? "men").toLowerCase();
  const mode: Mode = modeParam === "women" ? "women" : "men";

  // optional filters passed from navbar
  const category = (sp.get("category") ?? "").trim(); // e.g. "clothing"
  const group = (sp.get("group") ?? "all").trim(); // e.g. "Garment Upper body"

  const effectiveGroups = useMemo(() => {
    // If an explicit group was chosen, filter to that single group
    if (group && group !== "all") return [group];

    // Else if we have a category, filter to its group set
    const catGroups = CATEGORY_GROUPS[category];
    if (catGroups && catGroups.length) return catGroups;

    // Else no group filter (search across entire mode)
    return [];
  }, [category, group]);

  const groupsKey = useMemo(() => effectiveGroups.join("|"), [effectiveGroups]);

  const PAGE_SIZE = 48;

  const [items, setItems] = useState<Product[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(true);

  const sentinelRef = useRef<HTMLDivElement | null>(null);
  const offsetRef = useRef(0);
  const loadingRef = useRef(false);
  const hasMoreRef = useRef(true);

  function resolveImgSrc(imageUrl: string): string {
    const u = (imageUrl ?? "").trim();
    if (!u) return "";
    if (u.startsWith("http://") || u.startsWith("https://")) return u;
    // local fallback
    return `${API_BASE}${u.startsWith("/") ? "" : "/"}${u}`;
  }

  async function fetchSemanticProducts(opts: {
    q: string;
    mode: Mode;
    groups: string[];
    limit: number;
    offset: number;
  }): Promise<{ items: Product[]; total: number }> {
    const params = new URLSearchParams();
    params.set("q", opts.q);
    params.set("limit", String(opts.limit));
    params.set("offset", String(opts.offset));

    for (const g of opts.groups) params.append("product_group_name", g);

    // mode -> index groups (repeatable) to match your backend
    if (opts.mode === "men") {
      params.append("index_group_name", "Menswear");
    } else {
      params.append("index_group_name", "Ladieswear");
      params.append("index_group_name", "Divided");
    }

    const url = `${API_BASE}/products/semantic?${params.toString()}`;
    const resp = await fetch(url, { cache: "no-store" });

    if (!resp.ok) {
      const body = await resp.text().catch(() => "");
      throw new Error(`Semantic search failed (${resp.status}): ${body}`);
    }

    const data = await resp.json();
    return { items: data.items ?? [], total: data.total ?? 0 };
  }

  async function fetchKeywordProducts(opts: {
    q: string;
    mode: Mode;
    groups: string[];
    limit: number;
    offset: number;
  }): Promise<{ items: Product[]; total: number }> {
    const params = new URLSearchParams();
    params.set("q", opts.q);
    params.set("limit", String(opts.limit));
    params.set("offset", String(opts.offset));

    for (const g of opts.groups) params.append("product_group_name", g);

    // mode -> index groups (repeatable) to match your backend
    if (opts.mode === "men") {
      params.append("index_group_name", "Menswear");
    } else {
      params.append("index_group_name", "Ladieswear");
      params.append("index_group_name", "Divided");
    }

    const url = `${API_BASE}/products?${params.toString()}`;
    const resp = await fetch(url, { cache: "no-store" });

    if (!resp.ok) {
      const body = await resp.text().catch(() => "");
      throw new Error(`Search failed (${resp.status}): ${body}`);
    }

    const data = await resp.json();
    return { items: data.items ?? [], total: data.total ?? 0 };
  }

  const loadMore = useCallback(async () => {
    if (!q) return;
    if (loadingRef.current || !hasMoreRef.current) return;

    loadingRef.current = true;
    setLoading(true);
    setErr(null);

    try {
      const currOffset = offsetRef.current;

      // Try semantic first, fall back to keyword search if semantic is down
      let res: { items: Product[]; total: number };
      try {
        res = await fetchSemanticProducts({
          q,
          mode,
          groups: effectiveGroups,
          limit: PAGE_SIZE,
          offset: currOffset,
        });
      } catch (e) {
        res = await fetchKeywordProducts({
          q,
          mode,
          groups: effectiveGroups,
          limit: PAGE_SIZE,
          offset: currOffset,
        });
      }

      setTotal(res.total);

      setItems((prev) => {
        const seen = new Set(prev.map((p) => String(p.id)));
        const merged = [...prev];
        for (const p of res.items) {
          const id = String(p.id);
          if (!seen.has(id)) {
            seen.add(id);
            merged.push(p);
          }
        }
        return merged;
      });

      offsetRef.current = currOffset + res.items.length;

      if (res.items.length < PAGE_SIZE) {
        hasMoreRef.current = false;
        setHasMore(false);
      }
    } catch (e: any) {
      setErr(String(e?.message ?? e));
      hasMoreRef.current = false;
      setHasMore(false);
    } finally {
      loadingRef.current = false;
      setLoading(false);
    }
  }, [API_BASE, q, mode, groupsKey, effectiveGroups]);

  // Reset whenever q/mode/groups changes
  useEffect(() => {
    setItems([]);
    setTotal(0);
    setHasMore(true);
    setErr(null);

    offsetRef.current = 0;
    hasMoreRef.current = true;
    loadingRef.current = false;

    if (q) loadMore();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q, mode, groupsKey]);

  // Infinite scroll
  useEffect(() => {
    const el = sentinelRef.current;
    if (!el) return;

    const obs = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) loadMore();
      },
      { rootMargin: "800px 0px" }
    );

    obs.observe(el);
    return () => obs.disconnect();
  }, [loadMore]);

  return (
    <section className="mx-auto max-w-6xl px-4 py-10">
      <div className="mb-6 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-lg font-semibold tracking-tight text-neutral-900">
            SEARCH RESULT
          </h1>
          <h2>
            “{q}”{category ? ` • Category: ${category}` : ""}
          </h2>
          <h3>{group && group !== "all" ? `in: ${group}` : ""}</h3>
        </div>

        <div className="text-sm text-neutral-600">
          Showing {items.length}
          {total ? ` / ${total}` : ""} items
        </div>
      </div>

      {err ? (
        <div className="mb-6 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {err}
        </div>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {items.map((p) => {
          const imgSrc = resolveImgSrc(p.image_url);
          return (
            <Link
              key={String(p.id)}
              href={`/products/${p.id}`}
              className="group rounded-2xl border border-neutral-200 bg-white p-4 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
            >
              <img
                src={imgSrc}
                alt={p.name}
                className="aspect-[4/5] w-full rounded-xl bg-neutral-100 object-cover"
                loading="lazy"
              />
              <div className="mt-4">
                <div className="truncate text-sm font-medium text-neutral-900">
                  {p.name}
                </div>
                <div className="mt-1 text-sm text-neutral-600">
                  {formatUSD(p.price)}
                </div>
              </div>
            </Link>
          );
        })}
      </div>

      <div ref={sentinelRef} className="h-12" />

      <div className="mt-4 text-center text-sm text-neutral-600">
        {!q ? "" : loading ? "Loading more…" : hasMore ? "" : "End of results"}
      </div>
    </section>
  );
}
