export const dynamic = "force-dynamic";
export const revalidate = 0;

import Link from "next/link";
import { getHomepageProducts } from "@/lib/api";
import ImageCarousel from "@/components/ImageCarousel";
import ProductCatalog from "@/components/ProductCatalog";

type Mode = "men" | "women";

export default async function HomePageView({ mode = "men" }: { mode?: Mode }) {
  const [upper, footwear] = await Promise.all([
    getHomepageProducts({
      limit: 12,
      group: "Garment Upper body",
      mode,
    }),
    getHomepageProducts({
      limit: 12,
      group: "Shoes",
      mode,
    }),
  ]);

  const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

  return (
    <section className="mx-auto max-w-6xl px-4 pt-0">
      <div className="relative left-1/2 w-screen -translate-x-1/2 px-0">
        <ImageCarousel
          className="rounded-none border-x-0"
          heightClass="h-[400px]"
          slides={[
            { src: "/carousel/slide-1.jpg", alt: "" },
            { src: "/carousel/slide-2v2.jpg", alt: "" },
            { src: "/carousel/slide-3.jpg", alt: "" },
            { src: "/carousel/slide-4.jpg", alt: "" },
            { src: "/carousel/slide-5.jpg", alt: "" },
            { src: "/carousel/slide-6.jpg", alt: "" },
          ]}
          autoPlay
          intervalMs={4000}
        />
      </div>
      <div className="mt-10">
        <h2 className="text-2xl font-semibold tracking-tight text-neutral-900 sm:text-3xl">
          F E A T U R E D
        </h2>

        <ProductCatalog
          items={upper.items}
          apiBase={API_BASE}
          mode={mode}
          seeAllHref={mode === "men" ? "/men/products" : "/women/products"}
        />
      </div>

      {/* Featured Footwear */}
      <div className="mt-10">
        <ProductCatalog
          items={footwear.items}
          apiBase={API_BASE}
          mode={mode}
          seeAllHref={mode === "men" ? "/men/products" : "/women/products"}
        />
      </div>
    </section>
  );
}
