import { NextResponse } from "next/server";
import { getOrCreateSessionId } from "@/lib/session";

const BASE = process.env.API_BASE_URL!;

export async function GET(req: Request) {
  const sessionId = await getOrCreateSessionId();
  const url = new URL(req.url);

  // e.g. /api/recommendations?productId=123
  const upstream = new URL(`${BASE}/recommendations`);
  url.searchParams.forEach((v, k) => upstream.searchParams.set(k, v));

  const resp = await fetch(upstream.toString(), {
    headers: { "x-session-id": sessionId },
    cache: "no-store",
  });

  const text = await resp.text();
  return new NextResponse(text, {
    status: resp.status,
    headers: { "content-type": resp.headers.get("content-type") || "application/json" },
  });
}
