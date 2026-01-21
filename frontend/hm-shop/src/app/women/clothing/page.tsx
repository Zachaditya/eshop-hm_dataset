import ProductsCatalogPage from "@/components/ProductsCatalogPage";

export default function WomenClothingPage() {
  return (
    <ProductsCatalogPage
      mode="women"
      title="Clothing"
      groups={[
        "Garment Upper body",
        "Garment Lower body",
        "Garment Full body",
        "Underwear",
        "Socks & Tights",
        "Swimwear",
        "Nightwear",
      ]}
    />
  );
}
