import ProductsCatalogPage from "@/components/ProductsCatalogPage";

export default function WomenLifestylePage({
  searchParams,
}: {
  searchParams?: { group?: string; q?: string };
}) {
  return (
    <ProductsCatalogPage
      mode="women"
      title="Lifestyle"
      groups={["Items", "Furniture", "Stationery", "Garment and Shoe care"]}
      searchParams={searchParams}
    />
  );
}
