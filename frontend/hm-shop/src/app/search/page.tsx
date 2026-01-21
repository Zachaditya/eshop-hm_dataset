import SearchResultsPage from "@/components/SearchResultsPage";
import { Suspense } from "react";

export default function Page() {
  return (
    <Suspense
      fallback={<div className="mx-auto max-w-6xl px-4 py-10">Loading…</div>}
    >
      <SearchResultsPage />;
    </Suspense>
  );
}
