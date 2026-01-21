import ProductsCatalogPage from "@/components/ProductsCatalogPage";

export default function MenFootwearPage() {
  return (
    <ProductsCatalogPage
      mode="men"
      title="Footwear"
      groups={["Shoes", "Socks & Tights"]}
    />
  );
}
