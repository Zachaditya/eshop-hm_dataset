"use client";

import { useCart } from "@/components/CartProvider";
import Link from "next/link";

function formatUSD(cents: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(cents / 100);
}

export function CartContents({
  onCheckoutDone,
}: {
  onCheckoutDone?: (orderId?: string) => void;
}) {
  const { cart, loading, error, setQty, remove, clear, checkout } = useCart();

  if (loading) return <div className="text-sm opacity-70">Loading…</div>;
  if (error)
    return <div className="text-sm text-red-600">Cart error: {error}</div>;
  if (!cart || cart.items.length === 0)
    return <div className="text-sm opacity-70">Your cart is empty.</div>;

  return (
    <>
      <div className="mb-3 flex items-center justify-between">
        <div className="text-sm opacity-70">
          {cart.total_quantity} item{cart.total_quantity === 1 ? "" : "s"}
        </div>
        <button
          className="text-xs rounded-lg border px-2 py-1 hover:bg-black/5"
          onClick={clear}
        >
          Clear
        </button>
      </div>

      <div className="space-y-3">
        {cart.items.map((it) => {
          const name = it.product?.name ?? it.product_id;
          const unit = it.unit_price_cents;
          const line = it.line_total_cents;

          return (
            <div key={it.id} className="rounded-xl border border-black/10 p-3">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="truncate text-sm font-medium">{name}</div>
                  <div className="mt-1 text-xs opacity-70">
                    {unit != null ? formatUSD(unit) : "—"}
                  </div>
                </div>

                <div className="text-sm font-semibold">
                  {line != null ? formatUSD(line) : "—"}
                </div>
              </div>

              <div className="mt-3 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <button
                    className="h-8 w-8 rounded-lg border border-black/10 hover:bg-black/5"
                    onClick={() => setQty(it.id, Math.max(1, it.quantity - 1))}
                    aria-label="Decrease quantity"
                  >
                    −
                  </button>
                  <div className="w-8 text-center text-sm">{it.quantity}</div>
                  <button
                    className="h-8 w-8 rounded-lg border border-black/10 hover:bg-black/5"
                    onClick={() => setQty(it.id, it.quantity + 1)}
                    aria-label="Increase quantity"
                  >
                    +
                  </button>
                </div>

                <button
                  className="text-xs rounded-lg border border-black/10 px-2 py-1 hover:bg-black/5"
                  onClick={() => remove(it.id)}
                >
                  Remove
                </button>
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-4 border-t border-black/10 pt-4">
        <div className="flex items-center justify-between">
          <div className="text-sm opacity-70">Subtotal</div>
          <div className="text-sm font-semibold">
            {formatUSD(cart.subtotal_cents)}
          </div>
        </div>

        <Link
          href="/checkout"
          className="mt-3 block w-full rounded-xl bg-neutral-900 px-4 py-2.5 text-center text-sm font-medium text-white transition hover:bg-neutral-800 active:scale-[0.99]"
        >
          Checkout
        </Link>
      </div>
    </>
  );
}
