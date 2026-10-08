/** Cart operations sharing the storefront's guest-cart and login cookies. */
import { SESSION_API_BASE } from "./sessionApi";

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
  
  /**
   * Send a cart request through the same-origin backend proxy.
   * @param path Cart endpoint, starting with a slash.
   * @param init Optional method, headers, and JSON body.
   * @returns The decoded cart response, or a rejected promise for an API error.
   */
  async function http<T>(path: string, init?: RequestInit): Promise<T> {
    const resp = await fetch(`${SESSION_API_BASE}${path}`, {
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
    /**
     * Read or create the guest cart associated with the storefront cookie.
     * Params: None.
     * @returns The current cart, including its items and totals.
     */
    getCart: () => http<Cart>("/cart"),
  /**
   * Add a product to the current cart.
   * @param productId Catalog product identifier.
   * @param quantity Number of units to add; defaults to one.
   * @returns The updated cart.
   */
  addItem: (productId: string, quantity = 1) =>
    http<Cart>("/cart/items", {
      method: "POST",
      body: JSON.stringify({ product_id: productId, quantity }),
    }),
  /**
   * Replace a cart item's quantity.
   * @param itemId Identifier of the existing cart item.
   * @param quantity New quantity for that item.
   * @returns The updated cart.
   */
  setQuantity: (itemId: string, quantity: number) =>
    http<Cart>(`/cart/items/${itemId}`, {
      method: "PATCH",
      body: JSON.stringify({ quantity }),
    }),
  /**
   * Remove an item from the current cart.
   * @param itemId Identifier of the cart item to remove.
   * @returns The updated cart.
   */
  removeItem: (itemId: string) =>
    http<Cart>(`/cart/items/${itemId}`, { method: "DELETE" }),
  /**
   * Remove all items from the current cart.
   * Params: None.
   * @returns The empty cart.
   */
  clear: () => http<Cart>("/cart/clear", { method: "POST" }),


  /**
   * Finalize the authenticated account's current cart as an order.
   * Params: None.
   * @returns The order summary and the account's replacement active cart.
   */
  checkout: () => http<CheckoutResult>("/cart/checkout", { method: "POST" }),
  };
