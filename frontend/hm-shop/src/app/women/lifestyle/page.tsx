import ProductsCatalogPage from "@/components/ProductsCatalogPage";
import { Suspense } from "react";

export default function WomenLifestylePage() {
  return (
    <Suspense
      fallback={<div className="mx-auto max-w-6xl px-4 py-10">Loading…</div>}
    >
      <ProductsCatalogPage
        mode="women"
        title="Lifestyle"
        groups={["Items", "Furniture", "Stationery", "Garment and Shoe care"]}
      />
    </Suspense>
  );
}
