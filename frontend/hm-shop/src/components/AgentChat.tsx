"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { MessageCircle } from "lucide-react";

const META_MARKER = "\n\n<<HM_SHOP_PRODUCTS>>";

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";

type Role = "user" | "assistant" | "system";
type Msg = { role: Role; content: string };

type Product = {
  id: string;
  name: string;
  price?: number;
  image_url?: string;
  colour_group_name?: string;
  product_group_name?: string;
};

function formatUSD(n: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(n);
}

function cx(...xs: Array<string | false | undefined | null>) {
  return xs.filter(Boolean).join(" ");
}

// Robust streaming parser:
// - emits assistant text as it streams
// - if it sees META_MARKER, switches to buffering JSON
async function readAgentStream(
  resp: Response,
  onText: (delta: string) => void
): Promise<{ items: Product[] }> {
  const reader = resp.body?.getReader();
  if (!reader) return { items: [] };

  const decoder = new TextDecoder();
  const marker = META_MARKER;

  let inMeta = false;
  let pending = ""; // for detecting marker across chunk boundaries
  let metaBuf = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value, { stream: true });

    if (!inMeta) {
      pending += chunk;

      const idx = pending.indexOf(marker);
      if (idx >= 0) {
        // emit everything before marker
        const textPart = pending.slice(0, idx);
        if (textPart) onText(textPart);

        // switch to meta mode
        inMeta = true;
        metaBuf += pending.slice(idx + marker.length);
        pending = "";
      } else {
        // emit "safe" portion while keeping enough tail to detect marker split
        const keep = marker.length;
        if (pending.length > keep) {
          const emit = pending.slice(0, pending.length - keep);
          onText(emit);
          pending = pending.slice(pending.length - keep);
        }
      }
    } else {
      metaBuf += chunk;
    }
  }

  // flush any remaining text if we never saw marker
  if (!inMeta && pending) onText(pending);

  if (!inMeta) return { items: [] };

  try {
    const parsed = JSON.parse(metaBuf);
    return { items: Array.isArray(parsed?.items) ? parsed.items : [] };
  } catch {
    return { items: [] };
  }
}

export default function AgentChat() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Msg[]>([
    {
      role: "assistant",
      content: "Hey! Tell me what you’re looking for (type, color, occasion).",
    },
  ]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [recommended, setRecommended] = useState<Product[]>([]);

  const listRef = useRef<HTMLDivElement | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const API_BASE = useMemo(
    () => process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000",
    []
  );
  const sp = useSearchParams();

  const reduceMotion = useReducedMotion();

  // Auto-scroll on new tokens/messages
  useEffect(() => {
    if (!open) return;
    listRef.current?.scrollTo({
      top: listRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, recommended, open]);

  const uiMessages = useMemo(
    () => messages.filter((m) => m.role !== "system"),
    [messages]
  );

  async function send() {
    const text = input.trim();
    if (!text || busy) return;

    setInput("");
    setBusy(true);
    setRecommended([]); // clear old cards

    // build history BEFORE mutating state
    const history: Msg[] = messages
      .filter((m) => m.role !== "system")
      .map((m) => ({ role: m.role, content: m.content })) as Msg[];

    setMessages((prev) => [
      ...prev,
      { role: "user", content: text },
      { role: "assistant", content: "" },
    ]);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const payload = {
        mode: sp.get("mode") ?? undefined,
        category: sp.get("category") ?? undefined,
        group: sp.get("group") ?? undefined,
        messages: [...history, { role: "user", content: text }],
      };

      const resp = await fetch("/api/agent", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        signal: controller.signal,
      });

      if (!resp.ok || !resp.body) {
        const err = await resp.text().catch(() => "");
        throw new Error(err || `Request failed: ${resp.status}`);
      }

      let acc = "";
      const meta = await readAgentStream(resp, (delta) => {
        acc += delta;
        setMessages((prev) => {
          const next = [...prev];
          for (let i = next.length - 1; i >= 0; i--) {
            if (next[i].role === "assistant") {
              next[i] = { ...next[i], content: acc };
              break;
            }
          }
          return next;
        });
      });

      setRecommended(meta.items);
    } catch (e: any) {
      const msg = String(e?.message ?? e);
      setMessages((prev) => {
        const next = [...prev];
        for (let i = next.length - 1; i >= 0; i--) {
          if (next[i].role === "assistant") {
            next[i] = { role: "assistant", content: `⚠️ ${msg}` };
            break;
          }
        }
        return next;
      });
      setRecommended([]);
    } finally {
      abortRef.current = null;
      setBusy(false);
    }
  }

  function stop() {
    abortRef.current?.abort();
    abortRef.current = null;
    setBusy(false);
  }

  function close() {
    // abort streaming if closing mid-response
    abortRef.current?.abort();
    abortRef.current = null;
    setBusy(false);
    setOpen(false);
  }

  return (
    <>
      {/* Closed state: button */}
      {!open ? (
        <div className="fixed bottom-5 right-5 z-50">
          <button
            onClick={() => setOpen(true)}
            className="rounded-full border border-neutral-200 bg-white p-3 text-neutral-900 shadow-lg hover:bg-neutral-50"
            aria-label="Open chat"
            title="Chat"
          >
            <MessageCircle className="h-6 w-6 -scale-x-100" />
          </button>
        </div>
      ) : null}

      {/* Open state: animated overlay + panel (same pattern as CartDrawer) */}
      <AnimatePresence>
        {open ? (
          <motion.div
            className="fixed inset-0 z-50"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            {/* backdrop */}
            <motion.button
              aria-label="Close chat"
              className="absolute inset-0 bg-black/40"
              onClick={close}
              initial={{ opacity: 0 }}
              animate={{
                opacity: 1,
                transition: { duration: reduceMotion ? 0 : 0.18 },
              }}
              exit={{
                opacity: 0,
                transition: { duration: reduceMotion ? 0 : 0.12 },
              }}
            />

            {/* panel (RIGHT) */}
            <motion.div
              className="absolute bottom-5 right-5 w-[360px] overflow-hidden rounded-2xl border border-neutral-200 bg-white shadow-2xl"
              initial={reduceMotion ? { x: 0 } : { x: "100%" }}
              animate={
                reduceMotion
                  ? { x: 0 }
                  : {
                      x: 0,
                      transition: {
                        type: "spring",
                        stiffness: 220,
                        damping: 28,
                        mass: 1.0,
                      },
                    }
              }
              exit={
                reduceMotion
                  ? { x: 0 }
                  : {
                      x: "100%",
                      transition: { duration: 0.22, ease: "easeInOut" },
                    }
              }
            >
              {/* --- keep your existing chat panel UI below --- */}

              <div className="flex items-center justify-between border-b border-neutral-200 px-4 py-3">
                <div className="text-sm font-semibold text-neutral-900">
                  HM Assistant
                </div>
                <div className="flex items-center gap-2">
                  {busy ? (
                    <button
                      onClick={stop}
                      className="rounded-lg border border-neutral-200 bg-white px-2 py-1 text-xs text-neutral-700 hover:bg-neutral-50"
                    >
                      Stop
                    </button>
                  ) : null}
                  <button
                    onClick={close}
                    className="rounded-lg border border-neutral-200 bg-white px-2 py-1 text-xs text-neutral-700 hover:bg-neutral-50"
                  >
                    Close →
                  </button>
                </div>
              </div>

              <div
                ref={listRef}
                className="max-h-[420px] space-y-3 overflow-auto bg-neutral-50 px-4 py-3"
              >
                {uiMessages.map((m, idx) => (
                  <div
                    key={idx}
                    className={cx(
                      "max-w-[85%] whitespace-pre-wrap rounded-2xl px-3 py-2 text-sm",
                      m.role === "user"
                        ? "ml-auto bg-neutral-900 text-white"
                        : "mr-auto border border-neutral-200 bg-white text-neutral-900"
                    )}
                  >
                    {m.content || (m.role === "assistant" && busy ? "…" : "")}
                  </div>
                ))}

                {/* Your existing recommended block stays here unchanged */}
                {recommended.length > 0 ? (
                  <div className="mr-auto w-full rounded-2xl border border-neutral-200 bg-white p-3">
                    <div className="mb-2 text-xs font-semibold text-neutral-700">
                      Recommended
                    </div>

                    <div className="grid grid-cols-2 gap-2">
                      {recommended.map((p) => (
                        <Link
                          key={p.id}
                          href={`/products/${encodeURIComponent(String(p.id))}`}
                          className="rounded-xl border border-neutral-200 bg-white p-2 hover:bg-neutral-50"
                        >
                          {p.image_url ? (
                            // eslint-disable-next-line @next/next/no-img-element
                            <img
                              src={`${API_BASE}${p.image_url}`}
                              alt={p.name}
                              className="aspect-[4/5] w-full rounded-lg bg-neutral-100 object-cover"
                              loading="lazy"
                            />
                          ) : (
                            <div className="aspect-[4/5] w-full rounded-lg bg-neutral-100" />
                          )}
                          <div className="mt-2 truncate text-xs font-medium text-neutral-900">
                            {p.name}
                          </div>
                          <div className="mt-1 text-xs text-neutral-600">
                            {typeof p.price === "number"
                              ? formatUSD(p.price)
                              : ""}
                          </div>
                        </Link>
                      ))}
                    </div>
                  </div>
                ) : null}
              </div>

              <div className="border-t border-neutral-200 bg-white p-3">
                <div className="flex gap-2">
                  <input
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") send();
                    }}
                    placeholder="Ask about items, colors, outfits…"
                    className="flex-1 rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-900 placeholder:text-neutral-400 outline-none focus:border-neutral-400 focus:ring-2 focus:ring-neutral-200"
                  />
                  <button
                    onClick={send}
                    disabled={busy || !input.trim()}
                    className="rounded-xl bg-neutral-900 px-3 py-2 text-sm font-medium text-white hover:bg-neutral-800 disabled:opacity-50"
                  >
                    Send
                  </button>
                </div>
              </div>

              {/* --- end chat panel --- */}
            </motion.div>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </>
  );
}
