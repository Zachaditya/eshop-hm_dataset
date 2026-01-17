import { redirect } from "next/navigation";

// optional, but fine
export const dynamic = "force-dynamic";

export default function ChatbotInfoPage() {
  const IS_VERCEL = !!process.env.VERCEL || !!process.env.VERCEL_ENV;

  // If not on Vercel (local), don't show this page.
  if (!IS_VERCEL) {
    redirect("/"); // or redirect to wherever you want locally
  }

  return (
    <main className="mx-auto flex min-h-[calc(100vh-64px)] max-w-2xl flex-col justify-center px-6 py-14">
      <div className="rounded-2xl border border-black/10 bg-white p-6 shadow-sm">
        <h1 className="text-2xl font-semibold">Chatbot is available locally</h1>

        <p className="mt-3 text-sm leading-relaxed text-black/70">
          This chatbot demo is only available when running the project locally.
          If you’d like to see a live demo, email{" "}
          <a
            href="mailto:zachaditya@berkeley.edu?subject=Local%20chatbot%20demo%20request"
            className="font-medium text-black underline underline-offset-4"
          >
            zachaditya@berkeley.edu
          </a>
          .
        </p>

        <div className="mt-6 flex flex-wrap gap-3">
          <a
            href="mailto:zachaditya@berkeley.edu?subject=Local%20chatbot%20demo%20request"
            className="inline-flex items-center justify-center rounded-xl bg-black px-4 py-2 text-sm font-medium text-white hover:bg-black/90 transition-colors"
          >
            Email for demo
          </a>

          <a
            href="/"
            className="inline-flex items-center justify-center rounded-xl border border-black/10 bg-white px-4 py-2 text-sm font-medium text-black hover:bg-black/5 transition-colors"
          >
            Back home
          </a>
        </div>
      </div>
    </main>
  );
}
