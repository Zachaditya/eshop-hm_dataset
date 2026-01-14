import ProductsCatalogPage from "@/components/ProductsCatalogPage";

export default function MenClothingPage({
  searchParams,
}: {
  searchParams?: { group?: string; q?: string };
}) {
  return (
    <ProductsCatalogPage
      mode="men"
      title="Clothing"
      groups={[
        "Garment Upper body",
        "Garment Lower body",
        "Garment Full body",
        "Underwear",
        "Swimwear",
        "Nightwear",
      ]}
      searchParams={searchParams}
    />
  );
}
