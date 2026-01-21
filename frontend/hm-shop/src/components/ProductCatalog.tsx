"use client";

import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";

export type Mode = "men" | "women";

type ProductLike = {
  id: string | number;
  name: string;
  price: number;
  image_url: string;

  index_group_name?: string; // "Menswear" | "Ladieswear" | "Divided" ...
};

function formatUSD(n: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(n);
}

export default function ProductCatalog({
  items,
  apiBase,
  title,
  seeAllHref = "/products",
  mode,
  limit,
}: {
  items: ProductLike[];
  apiBase: string;
  title?: string;
  seeAllHref?: string;
  mode?: Mode; // optional
  limit?: number; // optional
}) {
  const reduceMotion = useReducedMotion();

  let shown = items;

  // filter to menswear / womenswear
  if (mode) {
    shown = shown.filter((p) => {
      const g = p.index_group_name;
      if (!g) return true;

      if (mode === "men") return g === "Menswear";
      return g === "Ladieswear" || g === "Divided";
    });
  }

  if (typeof limit === "number") {
    shown = shown.slice(0, limit);
  }

  const container = {
    hidden: {},
    show: {
      transition: {
        staggerChildren: reduceMotion ? 0 : 0.04,
        delayChildren: reduceMotion ? 0 : 0.04,
      },
    },
  } as const;

  const card = {
    hidden: {
      opacity: reduceMotion ? 1 : 0,
      y: reduceMotion ? 0 : 22,
      scale: reduceMotion ? 1 : 0.985,
      filter: reduceMotion ? "blur(0px)" : "blur(10px)",
    },
    show: {
      opacity: 1,
      y: 0,
      scale: 1,
      filter: "blur(0px)",
      transition: reduceMotion
        ? { duration: 0 }
        : {
            y: {
              type: "spring" as const,
              stiffness: 170,
              damping: 30,
              mass: 1.1,
            },
            scale: {
              type: "spring" as const,
              stiffness: 170,
              damping: 30,
              mass: 1.1,
            },

            opacity: { duration: 0.35 },

            filter: { duration: 0.5, ease: "easeOut" as const, delay: 0.01 },
          },
    },
  } as const;

  return (
    <div className="mt-12">
      <div className="mb-4 flex items-end justify-between">
        {title ? (
          <div className="text-sm font-semibold text-neutral-900">{title}</div>
        ) : (
          <div />
        )}

        <Link
          href={seeAllHref}
          className="text-sm text-neutral-700 hover:text-neutral-900"
          aria-label="See all products"
        >
          See all →
        </Link>
      </div>

      <motion.div
        variants={container}
        initial="hidden"
        whileInView="show"
        viewport={{ once: true, amount: 0.2 }}
        className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"
      >
        {shown.map((p) => (
          <motion.div
            key={p.id}
            variants={card}
            whileHover={reduceMotion ? undefined : { y: -4, scale: 1.01 }}
            transition={{ type: "spring", stiffness: 360, damping: 24 }}
            className="group will-change-transform"
          >
            <Link
              href={`/products/${p.id}`}
              className="block rounded-2xl border border-neutral-200 bg-white p-4 shadow-sm transition-shadow hover:shadow-md"
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={(() => {
                  const base = (apiBase ?? "").replace(/\/$/, "");
                  const raw = (p.image_url ?? "").trim();

                  if (!raw) return "/placeholder.png";

                  if (/^https?:\/\//i.test(raw)) return raw;

                  const path = raw.replace(/^\/+/, "");

                  const finalPath = path.startsWith("images_data/")
                    ? `images/${path.slice("images_data/".length)}`
                    : path;

                  return `${base}/${finalPath}`;
                })()}
                alt={p.name}
                className="aspect-[4/5] w-full rounded-xl bg-neutral-100 object-cover"
                loading="lazy"
                onError={(e) => {
                  const img = e.currentTarget as HTMLImageElement;
                  if (img.dataset.fallback !== "1") {
                    img.dataset.fallback = "1";
                    img.src = "/placeholder.png"; // put placeholder.png in /public
                  }
                }}
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
      </motion.div>
    </div>
  );
}
