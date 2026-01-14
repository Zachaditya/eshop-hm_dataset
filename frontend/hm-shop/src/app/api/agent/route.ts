import { NextResponse } from "next/server";
import { getOrCreateSessionId } from "@/lib/session";

const BASE = process.env.API_BASE_URL!;

export async function POST(req: Request) {
  const sessionId = await getOrCreateSessionId();
  const body = await req.text();

  const resp = await fetch(`${BASE}/agent`, {
    method: "POST",
    headers: {
      "content-type": req.headers.get("content-type") || "application/json",
      "x-session-id": sessionId,
    },
    body,
  });

  const text = await resp.text();
  return new NextResponse(text, {
    status: resp.status,
    headers: { "content-type": resp.headers.get("content-type") || "application/json" },
  });
}
