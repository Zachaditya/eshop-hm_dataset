// src/app/api/agent/route.ts
import { NextRequest } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const META_MARKER = "\n\n<<HM_SHOP_PRODUCTS>>";
//Only True Locally
const CHATBOT_ENABLED = process.env.NEXT_PUBLIC_CHATBOT_ENABLED === "false";



type ChatMessage = {
  role: "system" | "user" | "assistant";
  content: string;
};

type Product = {
  id: string;
  name: string;
  price?: number;
  image_url?: string;
  product_group_name?: string;
  colour_group_name?: string;
  index_group_name?: string;
  mode?: "men" | "women";
  description?: string;
};

const DEFAULT_SYSTEM_PROMPT = `
You are HM-Shop's shopping assistant.

Rules:
- If you receive a system message that starts with "CATALOG CONTEXT" and it contains items, you MUST recommend 1–3 items from that context by name (and optionally price). Do not suggest browsing the website in that case.
- Do NOT invent products. Only use products listed in CATALOG CONTEXT.
- If CATALOG CONTEXT says "No matches found", ask exactly ONE clarifying question and suggest 2 broader keywords.
- If asked about sizing/fit, say it isn’t available in this dataset.
- Be concise and friendly.
`.trim();

/** -------- Retrieval helpers (simple, fast, deterministic) -------- */

const STOPWORDS = new Set([
  "i",
  "me",
  "my",
  "you",
  "your",
  "we",
  "us",
  "a",
  "an",
  "the",
  "and",
  "or",
  "but",
  "help",
  "find",
  "looking",
  "look",
  "want",
  "need",
  "show",
  "give",
  "please",
  "something",
  "some",
  "any",
  "with",
  "for",
  "to",
  "of",
  "in",
  "on",
  "at",
  "from",
  "like",
  "that",
  "this",
  "it",
  "its",
  "catalog",
  "catalogue",
  "shop",
  "hm",
  "h&m",
  "formal",
  "casual",
  "attire",
  "wear",
  "outfit",
  "occasion",
]);

const COLOR_WORDS = new Set([
  "black",
  "white",
  "grey",
  "gray",
  "beige",
  "cream",
  "brown",
  "navy",
  "blue",
  "green",
  "red",
  "pink",
  "purple",
  "yellow",
  "orange",
  "silver",
  "gold",
  "khaki",
]);

function tokenize(raw: string) {
  return raw
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, " ")
    .split(/\s+/)
    .filter(Boolean);
}

function singularize(t: string) {
  return t.endsWith("s") && t.length > 3 ? t.slice(0, -1) : t;
}

function extractIntent(raw: string) {
  const toks = tokenize(raw).map(singularize);

  const color = toks.find((t) => COLOR_WORDS.has(t));

  const keywords = toks.filter((t) => !STOPWORDS.has(t) && !COLOR_WORDS.has(t));

  // Expand common garment synonyms so "jacket" can still find "blazer/coat"
  const terms = new Set<string>(keywords.slice(0, 5));
  if (terms.has("jacket")) {
    terms.add("blazer");
    terms.add("coat");
  }
  if (terms.has("blazer")) terms.add("jacket");
  if (terms.has("coat")) terms.add("jacket");

  return {
    color,
    terms: Array.from(terms).slice(0, 5), // keep small for speed
    raw,
  };
}

function hash32(str: string) {
  let h = 2166136261;
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

function uniqById(items: Product[]) {
  const seen = new Set<string>();
  const out: Product[] = [];
  for (const p of items) {
    if (!seen.has(p.id)) {
      seen.add(p.id);
      out.push(p);
    }
  }
  return out;
}

function colorMatch(p: Product, color?: string) {
  if (!color) return true;
  const c = String(p.colour_group_name ?? "").toLowerCase();
  const n = String(p.name ?? "").toLowerCase();
  return c.includes(color) || n.includes(color);
}

function keywordScore(p: Product, terms: string[]) {
  const hay = `${p.name ?? ""} ${p.description ?? ""} ${p.product_group_name ?? ""}`.toLowerCase();
  let s = 0;
  for (const t of terms) {
    if (!t) continue;
    if (hay.includes(t)) s += 2;
  }
  return s;
}

async function searchProductsViaNext(
  req: NextRequest,
  opts: {
    q?: string;
    limit?: number;
    offset?: number;
    mode?: "men" | "women";
    category?: string;
    group?: string;
  }
): Promise<Product[]> {
  const origin = new URL(req.url).origin;
  const url = new URL(`${origin}/api/products`);

  const qq = String(opts.q ?? "").trim();
  if (qq) url.searchParams.set("q", qq);

  url.searchParams.set("limit", String(opts.limit ?? 12));
  url.searchParams.set("offset", String(opts.offset ?? 0));
  if (opts.mode) url.searchParams.set("mode", opts.mode);
  if (opts.category) url.searchParams.set("category", opts.category);
  if (opts.group) url.searchParams.set("group", opts.group);

  const resp = await fetch(url.toString(), {
    cache: "no-store",
    // keep session behavior consistent with your existing /api/products
    headers: { cookie: req.headers.get("cookie") ?? "" },
  });

  if (!resp.ok) return [];
  const data = await resp.json();
  return Array.isArray(data?.items) ? (data.items as Product[]) : [];
}

/** -------- Route handlers -------- */

export async function GET() {
  return Response.json({ ok: true, route: "/api/agent" });
}

export async function POST(req: NextRequest) {
  let body: any;
  try {
    body = await req.json();
  } catch {
    return new Response("Invalid JSON body", { status: 400 });
  }

  if (!CHATBOT_ENABLED) {
    return new Response("This chatbot demo is only available when running the project locally. If you’d like to see a live demo, email zachaditya@berkeley.edu to schedule a demo", 
    { status: 403 });
  }

  const incoming: ChatMessage[] = Array.isArray(body?.messages) ? body.messages : [];
  if (!incoming.length) return new Response("No messages provided", { status: 400 });

  const messagesWithSystem: ChatMessage[] =
    incoming[0]?.role === "system"
      ? incoming
      : [{ role: "system", content: DEFAULT_SYSTEM_PROMPT }, ...incoming];

  const lastUser =
    [...messagesWithSystem].reverse().find((m) => m.role === "user")?.content ?? "";
  const qRaw = lastUser.trim();

  const mode = body?.mode as "men" | "women" | undefined;
  const category = body?.category as string | undefined;
  const group = body?.group as string | undefined;

  // 1) Retrieve items for UI (cards) + build catalog context for model grounding
  let uiItems: Product[] = [];
  let catalogContext = "";

  if (qRaw) {
    const { color, terms } = extractIntent(qRaw);

    // Try: term-by-term search (more forgiving than full sentence)
    let hits: Product[] = [];
    for (const term of terms.length ? terms : [qRaw]) {
      const part = await searchProductsViaNext(req, {
        q: term,
        limit: 24,
        offset: 0,
        mode,
        category,
        group,
      });
      hits.push(...part);
    }

    hits = uniqById(hits).filter((p) => colorMatch(p, color));

    // If still empty and user had a color, try searching by color alone,
    // then keep items that match any garment term (if present).
    if (!hits.length && color) {
      const byColor = await searchProductsViaNext(req, {
        q: color,
        limit: 48,
        offset: 0,
        mode,
        category,
        group,
      });
      const garmentTerms = terms.filter((t) => t !== color);
      hits = uniqById(byColor).filter((p) =>
        garmentTerms.length ? keywordScore(p, garmentTerms) > 0 : true
      );
    }

    // Browse fallback (vary offset so it's not always the same first product)
    if (!hits.length) {
      const off = hash32(`${qRaw}|${mode ?? ""}|${category ?? ""}|${group ?? ""}`) % 120;
      hits = await searchProductsViaNext(req, {
        q: "",
        limit: 48,
        offset: off,
        mode,
        category,
        group,
      });
    }

    // Rerank by keyword score (and color match)
    const ranked = uniqById(hits)
      .map((p) => {
        const s =
          keywordScore(p, terms) +
          (color ? (colorMatch(p, color) ? 3 : 0) : 0);
        return { p, s };
      })
      .sort((a, b) => b.s - a.s)
      .map((x) => x.p);

    uiItems = ranked.slice(0, 6);

    if (uiItems.length) {
      catalogContext =
        "CATALOG CONTEXT (real items; do not invent other items):\n" +
        uiItems
          .map((p, i) => {
            const price =
              typeof p.price === "number" ? `$${p.price.toFixed(2)}` : "Price N/A";
            return `${i + 1}. id=${p.id} | name=${p.name} | group=${p.product_group_name ?? ""} | color=${p.colour_group_name ?? ""} | mode=${p.mode ?? ""} | price=${price}`;
          })
          .join("\n");
    } else {
      catalogContext =
        `CATALOG CONTEXT:\nNo matches found for "${qRaw}". ` +
        `Ask one clarifying question and suggest 2 broader keywords.`;
    }
  }

  // 2) Inject catalog context as a system message right after the main system
  const finalMessages: ChatMessage[] = catalogContext
    ? [
        messagesWithSystem[0],
        { role: "system", content: catalogContext },
        ...messagesWithSystem.slice(1),
      ]
    : messagesWithSystem;

  // 3) Call Ollama
  const baseUrl = process.env.OLLAMA_BASE_URL ?? "http://127.0.0.1:11434";
  const model = process.env.OLLAMA_MODEL ?? "phi3:mini";

  const upstream = await fetch(`${baseUrl}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      model,
      messages: finalMessages,
      stream: true,
      keep_alive: "30m",
      options: {
        temperature: 0.3, // a bit lower = less rambling, more faithful to context
        num_ctx: 1024,
        num_predict: 180,
      },
    }),
  });

  if (!upstream.ok) {
    const errText = await upstream.text().catch(() => "");
    return new Response(`Ollama error: ${upstream.status}\n${errText}`, { status: 502 });
  }
  if (!upstream.body) return new Response("Ollama returned no body", { status: 502 });

  // 4) Stream tokens to client; always append META at end (even if final line lacks "\n")
  const decoder = new TextDecoder();
  const encoder = new TextEncoder();
  let buffer = "";
  let metaSent = false;

  const sendMeta = (controller: ReadableStreamDefaultController<Uint8Array>) => {
    if (metaSent) return;
    metaSent = true;
    const meta = JSON.stringify({ items: uiItems });
    controller.enqueue(encoder.encode(`${META_MARKER}${meta}`));
  };

  const stream = new ReadableStream<Uint8Array>({
    async start(controller) {
      const reader = upstream.body!.getReader();
      try {
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });

          const lines = buffer.split("\n");
          buffer = lines.pop() ?? "";

          for (const line of lines) {
            const s = line.trim();
            if (!s) continue;

            let obj: any;
            try {
              obj = JSON.parse(s);
            } catch {
              continue;
            }

            const token: string = obj?.message?.content ?? "";
            if (token) controller.enqueue(encoder.encode(token));

            if (obj?.done) {
              sendMeta(controller);
              controller.close();
              return;
            }
          }
        }

        // Flush leftover buffer (final JSON might not end with "\n")
        const tail = buffer.trim();
        if (tail) {
          try {
            const obj = JSON.parse(tail);
            const token: string = obj?.message?.content ?? "";
            if (token) controller.enqueue(encoder.encode(token));
            if (obj?.done) {
              sendMeta(controller);
              controller.close();
              return;
            }
          } catch {
            // ignore
          }
        }

        // Ensure UI meta is always appended
        sendMeta(controller);
        controller.close();
      } catch (e) {
        controller.error(e);
      }
    },
    cancel() {
      try {
        upstream.body?.cancel();
      } catch {}
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "Cache-Control": "no-store",
    },
  });
}
