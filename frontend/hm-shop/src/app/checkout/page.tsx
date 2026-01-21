"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useCart } from "@/components/CartProvider";

function formatUSDFromCents(cents: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(cents / 100);
}

export default function CheckoutPage() {
  const router = useRouter();
  const API_BASE = useMemo(
    () => process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000",
    []
  );

  const { cart, loading, error, refresh, checkout } = useCart();
  const [placing, setPlacing] = useState(false);
  const [placed, setPlaced] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function doCheckout() {
    setErr(null);
    setPlacing(true);
    try {
      await checkout(); // ✅ ONE checkout call
      setPlaced(true);
      setTimeout(() => router.push("/"), 2500);
    } catch (e: any) {
      setErr(e?.message ?? "Checkout failed");
    } finally {
      setPlacing(false);
    }
  }

  if (placed) {
    return (
      <div className="flex min-h-[calc(100vh-64px)] items-center justify-center px-4 py-10">
        <div className="text-center">
          <div className="text-2xl font-semibold">Order Placed!</div>
          <div className="mt-2 text-sm text-neutral-500">
            Taking you back home…
          </div>
        </div>
      </div>
    );
  }

  if (loading)
    return (
      <div className="mx-auto max-w-3xl px-4 py-10 text-sm text-neutral-500">
        Loading cart…
      </div>
    );

  if (error || err)
    return (
      <div className="mx-auto max-w-3xl px-4 py-10">
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {err ?? error}
          <div className="mt-3">
            <button
              onClick={() => refresh()}
              className="rounded-lg border border-red-200 bg-white px-3 py-1.5 text-sm font-medium hover:bg-red-50"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );

  if (!cart || cart.items.length === 0)
    return (
      <div className="mx-auto max-w-3xl px-4 py-10">
        <div className="rounded-2xl border border-neutral-200 bg-white p-6">
          <div className="text-sm text-neutral-600">Your cart is empty.</div>
          <button
            onClick={() => router.push("/")}
            className="mt-4 rounded-xl bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800"
          >
            Continue shopping
          </button>
        </div>
      </div>
    );

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <div className="mb-6">
        <h1 className="text-xl font-semibold">Checkout</h1>
        <div className="mt-1 text-sm text-neutral-500">
          Review your cart before placing the order.
        </div>
      </div>

      {/* Items */}
      <div className="rounded-2xl border border-neutral-200 bg-white">
        <div className="border-b border-neutral-200 px-5 py-4 text-sm font-medium">
          Cart items
        </div>

        <div className="divide-y divide-neutral-200">
          {cart.items.map((it) => {
            const name = it.product?.name ?? "Item";
            const qty = it.quantity;

            const pid = String(it.product?.id ?? it.product_id);
            const aid = pid.padStart(10, "0");

            // Local dev fallback (served by FastAPI static mount)
            const fallbackLocal = `${API_BASE}/images/${aid.slice(
              0,
              3
            )}/${aid}.jpg`;

            // Public R2 base (set in frontend env as NEXT_PUBLIC_IMAGE_BASE_URL)
            const IMAGE_BASE = (
              process.env.NEXT_PUBLIC_IMAGE_BASE_URL ?? ""
            ).replace(/\/$/, "");

            const imageKey =
              it.product?.image_key &&
              String(it.product.image_key).trim() !== ""
                ? String(it.product.image_key).replace(/^\/+/, "")
                : `images_data/${aid.slice(0, 3)}/${aid}.jpg`;

            const imgSrc = IMAGE_BASE
              ? `${IMAGE_BASE}/${imageKey}`
              : fallbackLocal;

            const line =
              it.line_total_cents ??
              (it.unit_price_cents != null ? it.unit_price_cents * qty : null);

            return (
              <div key={it.id} className="flex items-start gap-4 px-5 py-4">
                <div className="h-16 w-16 flex-shrink-0 overflow-hidden rounded-xl bg-neutral-100">
                  <img
                    src={imgSrc}
                    alt={name}
                    className="h-full w-full object-cover"
                    loading="lazy"
                    onError={(e) =>
                      ((e.currentTarget as HTMLImageElement).style.display =
                        "none")
                    }
                  />
                </div>

                <div className="min-w-0 flex-1">
                  <div className="truncate text-sm font-medium">{name}</div>
                  <div className="mt-1 text-xs text-neutral-500">
                    Qty: {qty}
                    {it.product?.color ? ` • ${it.product.color}` : ""}
                  </div>
                </div>

                <div className="text-right text-sm font-medium">
                  {line != null ? formatUSDFromCents(line) : "—"}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Summary BELOW items */}
      <div className="mt-6 rounded-2xl border border-neutral-200 bg-white p-5">
        <div className="text-sm font-medium">Order summary</div>

        <div className="mt-4 space-y-2 text-sm">
          <div className="flex items-center justify-between">
            <div className="text-neutral-600">Items</div>
            <div className="font-medium">{cart.total_quantity}</div>
          </div>
          <div className="flex items-center justify-between">
            <div className="text-neutral-600">Subtotal</div>
            <div className="font-medium">
              {formatUSDFromCents(cart.subtotal_cents)}
            </div>
          </div>
        </div>

        <button
          disabled={placing}
          onClick={doCheckout}
          className="mt-5 w-full rounded-xl bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-neutral-800 disabled:opacity-60"
        >
          {placing ? "Placing order…" : "Place order"}
        </button>

        <button
          onClick={() => router.push("/")}
          className="mt-3 w-full rounded-xl border border-neutral-200 bg-white px-4 py-2.5 text-sm font-medium hover:bg-neutral-50"
        >
          Back to shopping
        </button>
      </div>
    </div>
  );
}
