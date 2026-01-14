import { cookies } from "next/headers";
import crypto from "crypto";

const COOKIE_NAME = process.env.SESSION_COOKIE_NAME || "hm_session";

export async function getOrCreateSessionId(): Promise<string> {
  const jar = await cookies();

  const existing = jar.get(COOKIE_NAME)?.value;
  if (existing) return existing;

  const id = crypto.randomUUID();

  // Only works when called from a Route Handler or Server Action
  jar.set(COOKIE_NAME, id, {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    secure: process.env.NODE_ENV === "production",
    maxAge: 60 * 60 * 24 * 365,
  });

  return id;
}
