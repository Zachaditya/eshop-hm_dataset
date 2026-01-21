import ProductsCatalogPage from "@/components/ProductsCatalogPage";

export default function WomenFootwearPage() {
  return (
    <ProductsCatalogPage
      mode="women"
      title="Footwear"
      groups={["Shoes", "Socks & Tights"]}
    />
  );
}
