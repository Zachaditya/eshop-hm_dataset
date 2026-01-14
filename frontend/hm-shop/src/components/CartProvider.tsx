"use client";

import React, {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { cartApi, type Cart, type CheckoutResult } from "@/lib/cartApi";

type CartCtx = {
  cart: Cart | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  add: (productId: string, qty?: number) => Promise<void>;
  setQty: (itemId: string, qty: number) => Promise<void>;
  remove: (itemId: string) => Promise<void>;
  clear: () => Promise<void>;
  checkout: () => Promise<CheckoutResult>;
};

const Ctx = createContext<CartCtx | null>(null);

export default function CartProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [cart, setCart] = useState<Cart | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    setError(null);
    const c = await cartApi.getCart();
    setCart(c);
  }

  useEffect(() => {
    (async () => {
      try {
        await refresh();
      } catch (e: any) {
        setError(String(e?.message ?? e));
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const value = useMemo<CartCtx>(
    () => ({
      cart,
      loading,
      error,
      refresh: async () => {
        setLoading(true);
        try {
          await refresh();
        } finally {
          setLoading(false);
        }
      },
      add: async (productId, qty = 1) => {
        setError(null);
        const c = await cartApi.addItem(productId, qty);
        setCart(c);
      },
      setQty: async (itemId, qty) => {
        setError(null);
        const c = await cartApi.setQuantity(itemId, qty);
        setCart(c);
      },
      remove: async (itemId) => {
        setError(null);
        const c = await cartApi.removeItem(itemId);
        setCart(c);
      },
      clear: async () => {
        setError(null);
        const c = await cartApi.clear();
        setCart(c);
      },
      checkout: async () => {
        setError(null);
        const r = await cartApi.checkout();
        setCart(r.cart);
        return r; // so UI can show order_id
      },
    }),
    [cart, loading, error]
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useCart() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useCart must be used within CartProvider");
  return ctx;
}
