"use client";

import Link from "next/link";
import { usePathname, useSearchParams, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Search, User, ShoppingBag, ChevronDown } from "lucide-react";
import { useCart } from "@/components/CartProvider";
import { CartDrawer } from "@/components/CartDrawer";
import { useAuth } from "@/components/AuthProvider";

const TOP_TABS = [
  { label: "MEN", href: "/men" },
  { label: "WOMEN", href: "/women" },
];

const NAV_ITEMS: Array<{
  label: string;
  slug: string;
  children?: Array<{ label: string; group?: string }>;
}> = [
  {
    label: "Clothing",
    slug: "clothing",
    children: [
      { label: "All clothing", group: "all" },
      { label: "Upper garments", group: "Garment Upper body" },
      { label: "Lower garments", group: "Garment Lower body" },
      { label: "Full body", group: "Garment Full body" },
      { label: "Underwear", group: "Underwear" },
      { label: "Swimwear", group: "Swimwear" },
      { label: "Nightwear", group: "Nightwear" },
    ],
  },
  {
    label: "Footwear",
    slug: "footwear",
    children: [
      { label: "Shoes", group: "Shoes" },
      { label: "Socks & Tights", group: "Socks & Tights" },
    ],
  },
  {
    label: "Accessories",
    slug: "accessories",
    children: [
      { label: "Accessories", group: "Accessories" },
      { label: "Bags", group: "Bags" },
    ],
  },
  {
    label: "Lifestyle",
    slug: "lifestyle",
    children: [
      { label: "Items", group: "Items" },
      { label: "Furniture", group: "Furniture" },
      { label: "Stationery", group: "Stationery" },
      { label: "Garment & Shoe care", group: "Garment and Shoe care" },
    ],
  },
  { label: "Other", slug: "other" },
];

function cx(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(" ");
}

export default function Navbar() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const router = useRouter();

  // men/women based on path
  const mode = pathname.startsWith("/women") ? "women" : "men";
  const modeBase = mode === "women" ? "/women" : "/men";

  // Keep category when switching MEN/WOMEN (e.g., /men/clothing -> /women/clothing)
  const parts = pathname.split("/").filter(Boolean);
  const currentCategory =
    (parts[0] === "men" || parts[0] === "women") && parts[1] ? parts[1] : "";

  const menPath = currentCategory ? `/men/${currentCategory}` : "/men";
  const womenPath = currentCategory ? `/women/${currentCategory}` : "/women";

  const withParams = (path: string, next: Record<string, string | null>) => {
    const sp = new URLSearchParams(searchParams.toString());
    for (const [k, v] of Object.entries(next)) {
      if (v === null) sp.delete(k);
      else sp.set(k, v);
    }
    const qs = sp.toString();
    return qs ? `${path}?${qs}` : path;
  };

  // Dropdown open state
  const [openSlug, setOpenSlug] = useState<string | null>(null);
  const navRef = useRef<HTMLDivElement | null>(null);

  // Search state (sync with URL)
  const [q, setQ] = useState(searchParams.get("q") ?? "");
  useEffect(() => {
    setQ(searchParams.get("q") ?? "");
  }, [searchParams]);

  // Close on outside click + Escape
  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (!navRef.current) return;
      if (!navRef.current.contains(e.target as Node)) setOpenSlug(null);
    }
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") setOpenSlug(null);
    }
    document.addEventListener("mousedown", onDocClick);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onDocClick);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, []);

  // Close menus when route changes
  useEffect(() => {
    setOpenSlug(null);
    setCartOpen(false);
  }, [pathname]);

  // Search stays on the current page (preserves group, replaces q)
  const submitSearch = () => {
    const trimmed = q.trim();
    const params = new URLSearchParams();

    if (trimmed) params.set("q", trimmed);
    params.set("mode", mode);

    // carry context so search is “within” the current category/group
    if (currentCategory) params.set("category", currentCategory);

    const currentGroup = searchParams.get("group");
    if (currentGroup) params.set("group", currentGroup);

    router.push(`/search?${params.toString()}`);
  };

  // carts
  const { cart } = useCart();
  const count = cart?.total_quantity ?? 0;
  const [cartOpen, setCartOpen] = useState(false);

  // auth state
  const { user, loading } = useAuth();

  return (
    <header className="sticky top-0 z-50 border-b border-black/10 bg-white">
      <div className="mx-auto max-w-6xl px-6">
        {/* Top row */}
        <div className="grid h-16 grid-cols-3 items-center">
          {/* Left: MEN / WOMEN */}
          <div className="flex items-center gap-8">
            {TOP_TABS.map((t) => {
              const tabMode = t.href === "/women" ? "women" : "men";
              const isActive =
                tabMode === "women"
                  ? pathname === "/women" || pathname.startsWith("/women/")
                  : pathname === "/men" || pathname.startsWith("/men/");

              const basePath = tabMode === "women" ? womenPath : menPath;
              const href = withParams(basePath, {});

              return (
                <Link
                  key={t.label}
                  href={href}
                  className={cx(
                    "relative text-xs font-semibold tracking-[0.22em] transition",
                    isActive
                      ? "text-black after:absolute after:-bottom-2 after:left-0 after:h-[2px] after:w-full after:bg-black"
                      : "text-black/40 hover:text-black/70"
                  )}
                >
                  {t.label}
                </Link>
              );
            })}
          </div>

          {/* Center: logo */}
          <div className="flex justify-center">
            <Link
              href={modeBase}
              className="text-1xl font-extrabold tracking-[0.2em] text-black"
            >
              ESHOP (H&amp;M Catalog)
            </Link>
          </div>

          {/* Right: search + icons */}
          <div className="ml-auto flex items-center justify-end gap-4">
            <div className="hidden items-center gap-2 rounded-lg bg-black/5 px-1 py-2 md:flex">
              <Search className="h-4 w-4 text-black/60" />
              <input
                value={q}
                onChange={(e) => setQ(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && submitSearch()}
                className="w-56 bg-transparent text-sm text-black placeholder:text-black/50 focus:outline-none"
                placeholder={
                  mode === "women" ? "Search womenswear" : "Search menswear"
                }
              />
            </div>

            <Link
              href={loading ? "/login" : user ? "/account" : "/login"}
              className="rounded-lg p-2 hover:bg-black/5"
              aria-label="Account"
            >
              <User className="h-5 w-5" />
            </Link>

            <button
              type="button"
              className="relative rounded-lg p-2 hover:bg-black/5"
              aria-label={`Cart${count ? ` (${count} items)` : ""}`}
              onClick={() => setCartOpen(true)}
            >
              <ShoppingBag className="h-5 w-5" />
              {count > 0 && (
                <span className="absolute -right-1 -top-1 inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-neutral-900 px-1 text-[11px] font-semibold text-white">
                  {count}
                </span>
              )}
            </button>
          </div>
        </div>

        {/* Bottom row */}
        <nav
          ref={navRef}
          className="flex h-12 items-center justify-center gap-10"
        >
          {NAV_ITEMS.map((item) => {
            const basePath = `${modeBase}/${item.slug}`;

            const baseHref = withParams(basePath, { group: "all" });

            const isActive =
              pathname === basePath || pathname.startsWith(`${basePath}/`);

            const isOpen = openSlug === item.slug;

            return (
              <div
                key={item.slug}
                className="relative"
                onMouseEnter={() => setOpenSlug(item.slug)}
                onMouseLeave={() => setOpenSlug(null)}
              >
                <div className="flex items-center gap-1">
                  <Link
                    href={baseHref}
                    className={cx(
                      "text-sm transition",
                      isActive
                        ? "text-black font-medium"
                        : "text-black/80 hover:text-black"
                    )}
                  >
                    {item.label}
                  </Link>

                  <button
                    type="button"
                    aria-label={`${item.label} menu`}
                    aria-haspopup="menu"
                    aria-expanded={isOpen}
                    className="rounded-md p-1 text-black/60 hover:bg-black/5 hover:text-black"
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      setOpenSlug((v) => (v === item.slug ? null : item.slug));
                    }}
                  >
                    <ChevronDown
                      className={cx(
                        "h-4 w-4 transition",
                        isOpen && "rotate-180"
                      )}
                    />
                  </button>
                </div>

                {isOpen && item.children?.length ? (
                  <div
                    role="menu"
                    className="absolute left-1/2 top-full w-64 -translate-x-1/2 pt-2"
                  >
                    <div className="rounded-2xl border border-black/10 bg-white p-2 shadow-lg">
                      {item.children.map((c) => {
                        const href = withParams(basePath, {
                          group: c.group ?? "all",
                        });

                        const selectedGroup = searchParams.get("group");
                        const childActive =
                          isActive &&
                          ((c.group === "all" &&
                            (selectedGroup === "all" || !selectedGroup)) ||
                            selectedGroup === c.group);

                        return (
                          <Link
                            key={`${item.slug}:${c.label}`}
                            role="menuitem"
                            href={href}
                            className={cx(
                              "block rounded-xl px-3 py-2 text-sm transition",
                              childActive
                                ? "bg-black/5 text-black"
                                : "text-black/80 hover:bg-black/5 hover:text-black"
                            )}
                            onClick={() => setOpenSlug(null)}
                          >
                            {c.label}
                          </Link>
                        );
                      })}
                    </div>
                  </div>
                ) : null}
              </div>
            );
          })}
        </nav>
      </div>
      <CartDrawer open={cartOpen} onClose={() => setCartOpen(false)} />
    </header>
  );
}
