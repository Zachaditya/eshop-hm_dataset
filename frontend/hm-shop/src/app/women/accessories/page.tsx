import ProductsCatalogPage from "@/components/ProductsCatalogPage";

export default function WomenAccessoriesPage() {
  return (
    <ProductsCatalogPage
      mode="women"
      title="Accessories"
      groups={["Accessories", "Bags"]}
    />
  );
}
