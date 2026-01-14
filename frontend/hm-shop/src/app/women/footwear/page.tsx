import ProductsCatalogPage from "@/components/ProductsCatalogPage";

export default function WomenFootwearPage({
  searchParams,
}: {
  searchParams?: { group?: string; q?: string };
}) {
  return (
    <ProductsCatalogPage
      mode="women"
      title="Footwear"
      groups={["Shoes", "Socks & Tights"]}
      searchParams={searchParams}
    />
  );
}
