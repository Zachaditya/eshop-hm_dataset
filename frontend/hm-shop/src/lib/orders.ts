/** Order-history requests authenticated by the storefront session cookie. */
import { SESSION_API_BASE } from "./sessionApi";

export type OrderSummary = {
  order_id: string;
  ordered_at: string; 
  quantity_purchased: number;
  subtotal_cents: number;
};

/**
 * Load past orders for the currently authenticated demo account.
 * Params: None.
 * @returns The account's order summaries, or a rejected promise for an API error.
 */
export async function getOrders() {
  const resp = await fetch(`${SESSION_API_BASE}/orders`, {
    credentials: "include",
    cache: "no-store",
  });

  if (!resp.ok) {
    const text = await resp.text().catch(
      /** Recover from an unreadable error body. Params: None. Returns: Empty text. */
      () => ""
    );
    throw new Error(`Orders failed: ${resp.status} ${text}`);
  }

  return (await resp.json()) as { orders: OrderSummary[] };
}
