export type CartItem = {
    id: string;
    product_id: string;
    quantity: number;
    unit_price_cents: number | null;
    line_total_cents: number | null;
    product: {
      id: string;
      name: string | null;
      category?: string | null;
      image_key?: string | null;
      has_image?: boolean;
      color?: string | null;
    };
  };
  
  export type Cart = {
    id: string;
    user_id: string | null;
    status: string;
    items: CartItem[];
    total_quantity: number;
    subtotal_cents: number;
  };
  
  function apiBase() {
    return process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";
  }
  
  async function http<T>(path: string, init?: RequestInit): Promise<T> {
    const resp = await fetch(`${apiBase()}${path}`, {
      ...init,
      // IMPORTANT: cookie cart id is HttpOnly, so include credentials
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers ?? {}),
      },
      cache: "no-store",
    });
  
    if (!resp.ok) {
      let detail = `HTTP ${resp.status}`;
      try {
        const j = await resp.json();
        detail = j?.detail ?? JSON.stringify(j);
      } catch {}
      throw new Error(detail);
    }
    return resp.json();
  }

  export type CheckoutResult = {
    order_id: string;
    order_total_quantity: number;
    order_subtotal_cents: number;
    cart: Cart; 
  };
  
  export const cartApi = {
    getCart: () => http<Cart>("/cart"),
  addItem: (productId: string, quantity = 1) =>
    http<Cart>("/cart/items", {
      method: "POST",
      body: JSON.stringify({ product_id: productId, quantity }),
    }),
  setQuantity: (itemId: string, quantity: number) =>
    http<Cart>(`/cart/items/${itemId}`, {
      method: "PATCH",
      body: JSON.stringify({ quantity }),
    }),
  removeItem: (itemId: string) =>
    http<Cart>(`/cart/items/${itemId}`, { method: "DELETE" }),
  clear: () => http<Cart>("/cart/clear", { method: "POST" }),


  checkout: () => http<CheckoutResult>("/cart/checkout", { method: "POST" }),
  };
  
  