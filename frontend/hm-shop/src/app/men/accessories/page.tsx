import ProductsCatalogPage from "@/components/ProductsCatalogPage";

export default function AccessoriesPage() {
  return (
    <ProductsCatalogPage
      mode="men"
      title="Accessories"
      groups={["Accessories", "Bags"]}
    />
  );
}
