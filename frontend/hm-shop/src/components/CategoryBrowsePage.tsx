import { getProducts } from "@/lib/api";
import {
  CATEGORY_TO_PRODUCT_GROUPS,
  MODE_TO_INDEX_GROUPS,
} from "@/lib/catalog";

export default async function CategoryBrowsePage({
  mode,
  category,
  searchParams,
}: {
  mode: "men" | "women";
  category: string;
  searchParams?: { group?: string; q?: string };
}) {
  const group = searchParams?.group ?? "all";
  const q = searchParams?.q ?? "";

  const indexGroups = MODE_TO_INDEX_GROUPS[mode];

  const categoryGroups = CATEGORY_TO_PRODUCT_GROUPS[category] ?? [];
  const productGroups =
    group && group !== "all"
      ? [group]
      : categoryGroups.length
      ? categoryGroups
      : undefined; // "other" => no filter

  const data = await getProducts({
    index_group_name: indexGroups,
    product_group_name: productGroups,
    q,
    limit: 24,
    offset: 0,
  });

  return (
    <main className="mx-auto max-w-6xl px-6 py-8">
      <div className="mb-6 flex items-end justify-between gap-4">
        <div>
          <div className="text-sm text-black/60">Browsing</div>
          <h1 className="text-xl font-semibold">
            {mode.toUpperCase()} · {category}
            {group !== "all" ? ` · ${group}` : ""}
          </h1>
          {q ? (
            <div className="mt-1 text-sm text-black/60">Search: “{q}”</div>
          ) : null}
        </div>

        <div className="text-sm text-black/60">{data.total} items</div>
      </div>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
        {data.items.map((p) => (
          <div
            key={p.id}
            className="rounded-2xl border border-black/10 bg-white p-3 hover:shadow-sm"
          >
            <div className="aspect-[3/4] w-full overflow-hidden rounded-xl bg-black/5">
              <img
                src={`${
                  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000"
                }${p.image_url}`}
                alt={p.name}
                className="h-full w-full object-cover"
                loading="lazy"
              />
            </div>

            <div className="mt-3 text-sm font-medium">{p.name}</div>
            <div className="mt-1 text-xs text-black/60">
              {p.product_group_name}
            </div>
            <div className="mt-1 text-sm">${p.price.toFixed(2)}</div>
          </div>
        ))}
      </div>
    </main>
  );
}
