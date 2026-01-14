import Link from "next/link";

export default function NotFound() {
  return (
    <div className="mx-auto max-w-2xl px-4 py-16">
      <h1 className="text-2xl font-semibold tracking-tight">
        Product not found
      </h1>
      <p className="mt-2 text-neutral-600">
        This item doesn’t exist (or the backend couldn’t find it).
      </p>
      <Link
        href="/"
        className="mt-6 inline-block text-sm text-neutral-700 hover:text-neutral-900"
      >
        ← Back to home
      </Link>
    </div>
  );
}
