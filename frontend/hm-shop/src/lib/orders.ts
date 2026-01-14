const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export type OrderSummary = {
  order_id: string;
  ordered_at: string; 
  quantity_purchased: number;
  subtotal_cents: number;
};

export async function getOrders() {
  const resp = await fetch(`${API_BASE}/orders`, {
    credentials: "include",
    cache: "no-store",
  });

  if (!resp.ok) {
    const text = await resp.text().catch(() => "");
    throw new Error(`Orders failed: ${resp.status} ${text}`);
  }

  return (await resp.json()) as { orders: OrderSummary[] };
}
