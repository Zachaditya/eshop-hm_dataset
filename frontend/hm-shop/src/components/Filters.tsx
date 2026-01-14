"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useMemo, useState } from "react";

export function Filters() {
  const router = useRouter();
  const sp = useSearchParams();

  const initialQ = sp.get("q") || "";
  const [q, setQ] = useState(initialQ);

  const current = useMemo(() => {
    const out = new URLSearchParams(sp.toString());
    return out;
  }, [sp]);

  function apply() {
    const next = new URLSearchParams(current);
    if (q.trim()) next.set("q", q.trim());
    else next.delete("q");
    router.push(`/products?${next.toString()}`);
  }

  function clear() {
    router.push("/products");
    setQ("");
  }

  return (
    <div className="flex flex-col gap-3 rounded-2xl border p-4 sm:flex-row sm:items-end">
      <div className="flex-1">
        <div className="text-xs opacity-70">Search</div>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          className="mt-1 w-full rounded-xl border px-3 py-2 text-sm"
          placeholder="hoodie, shoes, etc."
        />
      </div>

      <div className="flex gap-2">
        <button onClick={apply} className="rounded-xl border px-4 py-2 text-sm">
          Apply
        </button>
        <button onClick={clear} className="rounded-xl border px-4 py-2 text-sm">
          Clear
        </button>
      </div>
    </div>
  );
}
