import { NextResponse } from "next/server";
import { getOrCreateSessionId } from "@/lib/session";

const BASE = process.env.API_BASE_URL;

export async function GET(req: Request) {
  if (!BASE) {
    return NextResponse.json(
      { detail: "Missing API_BASE_URL env var" },
      { status: 500 }
    );
  }

  const sessionId = await getOrCreateSessionId();
  const url = new URL(req.url);

  // Build upstream URL safely (avoids accidental double slashes)
  const upstream = new URL("products", BASE.endsWith("/") ? BASE : `${BASE}/`);

  // Preserve the exact query string, INCLUDING duplicate params
  upstream.search = url.search;

  const resp = await fetch(upstream.toString(), {
    headers: { "x-session-id": sessionId },
    cache: "no-store",
  });

  const text = await resp.text();
  return new NextResponse(text, {
    status: resp.status,
    headers: {
      "content-type": resp.headers.get("content-type") || "application/json",
    },
  });
}
