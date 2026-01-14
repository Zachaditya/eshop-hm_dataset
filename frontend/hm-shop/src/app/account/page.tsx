"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { CircleUser } from "lucide-react";

import { useAuth } from "@/components/AuthProvider";
import { getOrders } from "@/lib/orders";

type OrderRow = {
  order_id: string;
  ordered_at?: string; // if your backend returns this
  created_at?: string; // if your backend returns this instead
  quantity_purchased?: number;
  subtotal_cents?: number;
  items?: Array<{ product_id: string; name: string; quantity: number }>;
};

function formatUSDFromCents(cents?: number) {
  const v = typeof cents === "number" ? cents : 0;
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(v / 100);
}

function formatDate(iso?: string) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "2-digit",
  });
}

export default function AccountPage() {
  const router = useRouter();
  const { user, loading, logout } = useAuth();

  const [orders, setOrders] = useState<OrderRow[]>([]);
  const [ordersLoading, setOrdersLoading] = useState(false);
  const [ordersErr, setOrdersErr] = useState<string | null>(null);

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  useEffect(() => {
    let alive = true;

    async function load() {
      if (!user) return;
      setOrdersErr(null);
      setOrdersLoading(true);
      try {
        const data = await getOrders();
        if (!alive) return;
        setOrders(data.orders ?? []);
      } catch (e: any) {
        if (!alive) return;
        setOrdersErr(e?.message ?? "Failed to load orders");
      } finally {
        if (alive) setOrdersLoading(false);
      }
    }

    load();
    return () => {
      alive = false;
    };
  }, [user]);

  const rows = useMemo(() => {
    return (orders ?? []).map((o) => {
      const dateIso = o.ordered_at ?? o.created_at;
      // If you only return items (older orders endpoint), derive quantity/subtotal if possible
      const qty =
        typeof o.quantity_purchased === "number"
          ? o.quantity_purchased
          : Array.isArray(o.items)
          ? o.items.reduce((s, it) => s + (it.quantity ?? 0), 0)
          : 0;

      const subtotal =
        typeof o.subtotal_cents === "number" ? o.subtotal_cents : undefined; // if you didn’t return subtotal, we’ll show —

      return {
        id: o.order_id,
        dateIso,
        qty,
        subtotal,
      };
    });
  }, [orders]);

  if (loading) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-10">
        <div className="text-sm text-neutral-500">Loading account…</div>
      </div>
    );
  }

  if (!user) return null;

  return (
    <div className="min-h-[calc(100vh-64px)] bg-neutral-50 px-4 py-10">
      <div className="mx-auto w-full max-w-2xl">
        {/* Header / Profile */}
        <div className="rounded-2xl border border-neutral-200 bg-white p-6">
          <div className="text-center">
            <CircleUser className="mx-auto h-24 w-24 text-neutral-300" />

            <div className="mt-4 text-xl font-semibold">
              {user.name ?? "Account"}
            </div>
            <div className="mt-1 text-sm text-neutral-600">
              Email: {user.email}
            </div>

            <button
              onClick={async () => {
                await logout();
                router.push("/");
              }}
              className="mx-auto mt-6 inline-flex rounded-xl border border-neutral-200 bg-white px-4 py-2 text-sm font-medium hover:bg-neutral-50"
            >
              Log out
            </button>
          </div>
        </div>

        {/* Orders */}
        <div className="mt-6 rounded-2xl border border-neutral-200 bg-white p-6">
          <div className="mb-4 flex items-end justify-between gap-3">
            <div>
              <div className="text-base font-semibold">Past orders</div>
              <div className="mt-1 text-sm text-neutral-600">
                Order history for this account.
              </div>
            </div>
            <button
              onClick={async () => {
                setOrdersErr(null);
                setOrdersLoading(true);
                try {
                  const data = await getOrders();
                  setOrders(data.orders ?? []);
                } catch (e: any) {
                  setOrdersErr(e?.message ?? "Failed to load orders");
                } finally {
                  setOrdersLoading(false);
                }
              }}
              className="rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm font-medium hover:bg-neutral-50 disabled:opacity-60"
              disabled={ordersLoading}
            >
              {ordersLoading ? "Refreshing…" : "Refresh"}
            </button>
          </div>

          {ordersErr && (
            <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {ordersErr}
            </div>
          )}

          {ordersLoading ? (
            <div className="text-sm text-neutral-500">Loading orders…</div>
          ) : rows.length === 0 ? (
            <div className="rounded-xl border border-neutral-200 bg-neutral-50 px-4 py-4 text-sm text-neutral-600">
              No orders yet.
            </div>
          ) : (
            <div className="overflow-hidden rounded-xl border border-neutral-200">
              <table className="w-full text-left text-sm">
                <thead className="bg-neutral-50 text-neutral-600">
                  <tr>
                    <th className="px-4 py-3 font-medium">Order ID</th>
                    <th className="px-4 py-3 font-medium">Date</th>
                    <th className="px-4 py-3 font-medium">Qty</th>
                    <th className="px-4 py-3 font-medium text-right">
                      Subtotal
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-neutral-200">
                  {rows.map((r) => (
                    <tr key={r.id} className="bg-white">
                      <td className="px-4 py-3">
                        <div className="max-w-[180px] truncate font-mono text-[12px] text-neutral-700">
                          {r.id}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-neutral-700">
                        {formatDate(r.dateIso)}
                      </td>
                      <td className="px-4 py-3 text-neutral-700">{r.qty}</td>
                      <td className="px-4 py-3 text-right text-neutral-900">
                        {typeof r.subtotal === "number"
                          ? formatUSDFromCents(r.subtotal)
                          : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
