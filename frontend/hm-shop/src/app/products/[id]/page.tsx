import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";
import { getProduct, getSimilarProducts } from "../../../lib/api";

import { AddtoCart } from "@/components/AddtoCart";

function formatUSD(n: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(n);
}

export default async function ProductDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

  let product;
  try {
    product = await getProduct(id);
  } catch (e: any) {
    const msg = String(e?.message ?? "");
    if (msg.includes(" 404 ")) return notFound();
    throw e;
  }
  const { items: similar } = await getSimilarProducts(id, { limit: 8 });

  const imgSrc = `${API_BASE}${product.image_url}`;

  return (
    <div className="mx-auto max-w-6xl px-4 py-10">
      <div className="mb-6 flex items-center justify-between">
        <Link
          href="/"
          className="text-sm text-neutral-600 hover:text-neutral-900"
        >
          ← Back
        </Link>
      </div>

      <div className="grid gap-8 lg:grid-cols-2 lg:items-start">
        <div className="overflow-hidden rounded-3xl border border-neutral-200 bg-neutral-100">
          <div className="relative aspect-[4/5] w-full">
            <Image
              src={imgSrc}
              alt={product.name}
              fill
              className="object-cover"
              sizes="(min-width: 1024px) 50vw, 100vw"
              unoptimized
              priority
            />
          </div>
        </div>

        <div className="rounded-3xl border border-neutral-200 bg-white p-7 shadow-sm">
          <div className="text-xs text-neutral-500">
            {product.product_group_name ?? "Product"}
          </div>

          <h1 className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">
            {product.name}
          </h1>

          <div className="mt-3 text-lg font-medium">
            {formatUSD(product.price)}
          </div>

          <div className="mt-6 flex gap-3">
            <AddtoCart productId={String(product.id)} />
          </div>

          <div className="mt-10">
            <h2 className="text-sm font-semibold tracking-tight text-neutral-900">
              Description
            </h2>

            {product.description ? (
              <p className="mt-3 text-sm text-muted whitespace-pre-line">
                {product.description}
              </p>
            ) : (
              <p className="mt-3 text-sm text-muted">
                No description available yet.
              </p>
            )}
          </div>
        </div>
      </div>
      <div className="mt-12">
        <h2 className="text-sm font-semibold tracking-tight text-neutral-900">
          Similar products
        </h2>

        <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {similar.map((p) => (
            <Link
              key={p.id}
              href={`/products/${encodeURIComponent(String(p.id))}`}
              className="group rounded-2xl border border-neutral-200 bg-white p-4 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
            >
              <img
                src={`${API_BASE}${p.image_url}`}
                alt={p.name}
                className="aspect-[4/5] w-full rounded-xl bg-neutral-100 object-cover"
                loading="lazy"
              />
              <div className="mt-3">
                <div className="truncate text-sm font-medium">{p.name}</div>
                <div className="mt-1 text-sm text-muted">
                  {formatUSD(p.price)}
                </div>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
