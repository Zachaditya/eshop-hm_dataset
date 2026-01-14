"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { me as apiMe, logout as apiLogout } from "@/lib/auth";

type User = { id: string; email: string; name?: string | null };

type AuthCtx = {
  user: User | null;
  loading: boolean;
  refresh: () => Promise<void>;
  logout: () => Promise<void>;
};

const Ctx = createContext<AuthCtx | null>(null);

export default function AuthProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  async function refresh() {
    try {
      const u = await apiMe();
      setUser(u);
    } catch {
      setUser(null);
    }
  }

  async function logout() {
    try {
      await apiLogout();
    } finally {
      setUser(null);
    }
  }

  useEffect(() => {
    (async () => {
      setLoading(true);
      await refresh();
      setLoading(false);
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const value = useMemo(
    () => ({ user, loading, refresh, logout }),
    [user, loading]
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth() {
  const v = useContext(Ctx);
  if (!v) throw new Error("useAuth must be used within <AuthProvider />");
  return v;
}
