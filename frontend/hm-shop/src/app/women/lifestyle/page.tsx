import ProductsCatalogPage from "@/components/ProductsCatalogPage";

export default function WomenLifestylePage() {
  return (
    <ProductsCatalogPage
      mode="women"
      title="Lifestyle"
      groups={["Items", "Furniture", "Stationery", "Garment and Shoe care"]}
    />
  );
}
