import ProductsCatalogPage from "@/components/ProductsCatalogPage";
import { Suspense } from "react";

export default function WomenOtherPage() {
  return (
    <Suspense
      fallback={<div className="mx-auto max-w-6xl px-4 py-10">Loading…</div>}
    >
      <ProductsCatalogPage mode="women" title="Other" groups={["Unknown"]} />
    </Suspense>
  );
}
