"use client";

import Link from "next/link";
import type { Product } from "@/lib/types";

export function ProductCard({ product }: { product: Product }) {
  return (
    <div className="rounded-2xl border p-4">
      <div className="text-sm opacity-70">{product.category || "Product"}</div>
      <div className="mt-1 font-medium">{product.name}</div>
      <div className="mt-2 text-sm">
        {product.currency || "USD"} {product.price.toFixed(2)}
      </div>

      <div className="mt-4 flex items-center justify-between">
        <Link className="underline text-sm" href={`/products/${product.id}`}>
          View
        </Link>
        <button className="rounded-xl border px-3 py-1.5 text-sm">Add</button>
      </div>
    </div>
  );
}
