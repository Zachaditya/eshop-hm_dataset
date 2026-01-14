import { CartContents } from "@/components/CartContents";

export default function CartPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <h1 className="text-2xl font-semibold tracking-tight">Your cart</h1>
      <div className="mt-6 rounded-2xl border border-black/10 bg-white p-5 shadow-sm">
        <CartContents />
      </div>
    </div>
  );
}
