import ProductsCatalogPage from "@/components/ProductsCatalogPage";

export default function MenClothingPage({}) {
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
    />
  );
}
