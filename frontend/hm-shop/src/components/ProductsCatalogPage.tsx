"use client";

import { useEffect, useMemo, useRef, useState, useCallback } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { motion, useReducedMotion, type Variants } from "framer-motion";

type Mode = "men" | "women";

type Product = {
  id: string | number;
  name: string;
  price: number;
  image_url: string;
  index_group_name?: string;
};

function formatUSD(n: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(n);
}

export default function ProductsCatalogPage({
  mode,
  title,
  groups,
}: {
  mode: Mode;
  title: string;
  groups?: string[];
}) {
  const reduceMotion = useReducedMotion();

  const API_BASE = useMemo(
    () => process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000",
    []
  );
  const sp = useSearchParams();

  const selectedGroup = sp.get("group") ?? "all";
  const q = sp.get("q") ?? "";

  // if URL has group=... (not all), override groups with that single group
  const effectiveGroups = useMemo(() => {
    if (selectedGroup && selectedGroup !== "all") return [selectedGroup];
    return groups?.length ? groups : ["Garment Upper body"];
  }, [groups, selectedGroup]);

  const groupsKey = useMemo(() => effectiveGroups.join("|"), [effectiveGroups]);

  const PAGE_SIZE = 48;

  const [items, setItems] = useState<Product[]>([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(true);

  const sentinelRef = useRef<HTMLDivElement | null>(null);

  const offsetRef = useRef(0);
  const loadingRef = useRef(false);
  const hasMoreRef = useRef(true);

  const cardVariants: Variants = {
    hidden: {
      opacity: reduceMotion ? 1 : 0,
      y: reduceMotion ? 0 : 22,
      scale: reduceMotion ? 1 : 0.985,
      filter: reduceMotion ? "blur(0px)" : "blur(10px)",
    },
    show: (i: number) => {
      const base = reduceMotion ? 0 : 0.08;
      const stagger = reduceMotion ? 0 : 0.06;
      const cycle = 12; // repeat every N items
      const delay = Math.min(base + (i % cycle) * stagger, 0.6);

      return {
        opacity: 1,
        y: 0,
        scale: 1,
        filter: "blur(0px)",
        transition: reduceMotion
          ? { duration: 0 }
          : {
              // a bit faster, still smooth
              y: {
                type: "spring" as const,
                stiffness: 200,
                damping: 28,
                mass: 1.0,
              },
              scale: {
                type: "spring" as const,
                stiffness: 200,
                damping: 28,
                mass: 1.0,
              },

              // faster fade
              opacity: { duration: 0.22 },

              // faster blur clear
              filter: { duration: 0.32, ease: "easeOut" as const, delay: 0.0 },
            },
      };
    },
  };

  // Fetch function uses backend directly (not /api/products)
  async function fetchProducts(opts: {
    mode: Mode;
    groups: string[];
    q?: string;
    limit: number;
    offset: number;
  }) {
    const params = new URLSearchParams();
    params.set("limit", String(opts.limit));
    params.set("offset", String(opts.offset));

    // group filters (repeatable)
    for (const g of opts.groups ?? []) {
      params.append("product_group_name", g);
    }

    // mode -> index groups (repeatable)
    if (opts.mode === "men") {
      params.append("index_group_name", "Menswear");
    } else {
      params.append("index_group_name", "Ladieswear");
      params.append("index_group_name", "Divided");
    }

    if (opts.q?.trim()) params.set("q", opts.q.trim());

    const url = `${API_BASE}/products?${params.toString()}`;
    const resp = await fetch(url, { cache: "no-store" });

    if (!resp.ok) {
      const body = await resp.text().catch(() => "");
      throw new Error(`API error ${resp.status}: ${body}`);
    }

    const data = await resp.json();
    return (data.items ?? data) as Product[];
  }

  const loadMore = useCallback(async () => {
    if (loadingRef.current || !hasMoreRef.current) return;

    loadingRef.current = true;
    setLoading(true);
    setErr(null);

    try {
      const currOffset = offsetRef.current;

      const next = await fetchProducts({
        mode,
        groups: effectiveGroups,
        q,
        limit: PAGE_SIZE,
        offset: currOffset,
      });

      // Dedupe by id when appending
      setItems((prev) => {
        const seen = new Set(prev.map((p) => String(p.id)));
        const merged = [...prev];

        for (const p of next) {
          const id = String(p.id);
          if (!seen.has(id)) {
            seen.add(id);
            merged.push(p);
          }
        }
        return merged;
      });

      offsetRef.current = currOffset + next.length;

      if (next.length < PAGE_SIZE) {
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
  }, [API_BASE, mode, groupsKey, q, effectiveGroups]);

  useEffect(() => {
    setItems([]);
    setHasMore(true);
    setErr(null);

    offsetRef.current = 0;
    hasMoreRef.current = true;
    loadingRef.current = false;

    loadMore();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, groupsKey, q]);

  // Intersection observer
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
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-lg font-semibold tracking-tight text-neutral-900">
            {mode === "men" ? "Menswear" : "Womenswear"} · {title}
          </h1>
        </div>

        <div className="text-sm text-neutral-600">
          Showing {items.length} items
        </div>
      </div>

      {err ? (
        <div className="mb-6 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {err}
        </div>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {items.map((p, idx) => (
          <motion.div
            key={String(p.id)}
            variants={cardVariants}
            initial="hidden"
            whileInView="show"
            viewport={{ once: true, amount: 0.2 }}
            custom={idx}
            whileHover={
              reduceMotion ? undefined : ({ y: -3, scale: 1.01 } as const)
            }
            transition={
              reduceMotion
                ? undefined
                : ({
                    type: "spring" as const,
                    stiffness: 200,
                    damping: 28,
                    mass: 1.0,
                  } as const)
            }
            className="group will-change-transform"
          >
            <Link
              href={`/products/${p.id}`}
              className="block rounded-2xl border border-neutral-200 bg-white p-4 shadow-sm transition-shadow hover:shadow-md"
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={`${API_BASE}${p.image_url}`}
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
          </motion.div>
        ))}
      </div>

      <div ref={sentinelRef} className="h-12" />

      <div className="mt-4 text-center text-sm text-neutral-600">
        {loading ? "Loading more…" : hasMore ? "" : "End of catalog"}
      </div>
    </section>
  );
}
