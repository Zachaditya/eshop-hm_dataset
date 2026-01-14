import ProductsCatalogPage from "@/components/ProductsCatalogPage";

export default function MenFootwearPage({
  searchParams,
}: {
  searchParams?: { group?: string; q?: string };
}) {
  return (
    <ProductsCatalogPage
      mode="men"
      title="Footwear"
      groups={["Shoes", "Socks & Tights"]}
      searchParams={searchParams}
    />
  );
}
