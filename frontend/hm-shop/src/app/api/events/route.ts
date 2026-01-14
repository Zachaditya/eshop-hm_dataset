import { NextResponse } from "next/server";
import { getOrCreateSessionId } from "@/lib/session";

const BASE = process.env.API_BASE_URL!;

export async function GET() {
  const sessionId = await getOrCreateSessionId();
  const resp = await fetch(`${BASE}/events`, {
    headers: { "x-session-id": sessionId },
    cache: "no-store",
  });

  const text = await resp.text();
  return new NextResponse(text, {
    status: resp.status,
    headers: { "content-type": resp.headers.get("content-type") || "application/json" },
  });
}
