import ProductsCatalogPage from "@/components/ProductsCatalogPage";

export default function WomenAccessoriesPage({
  searchParams,
}: {
  searchParams?: { group?: string; q?: string };
}) {
  return (
    <ProductsCatalogPage
      mode="women"
      title="Accessories"
      groups={["Accessories", "Bags"]}
      searchParams={searchParams}
    />
  );
}
