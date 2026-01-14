"use client";

import { useState } from "react";
import { agentChat } from "@/lib/api";

export function AgentChat() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<
    { role: "user" | "agent"; text: string }[]
  >([]);
  const [loading, setLoading] = useState(false);

  async function send() {
    const text = input.trim();
    if (!text || loading) return;

    setMessages((m) => [...m, { role: "user", text }]);
    setInput("");
    setLoading(true);

    try {
      const resp = await agentChat({ message: text });
      setMessages((m) => [...m, { role: "agent", text: resp.reply }]);
    } catch (e: any) {
      setMessages((m) => [
        ...m,
        { role: "agent", text: `Error: ${e?.message || String(e)}` },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="rounded-2xl border p-4">
      <div className="text-sm font-medium">Agent</div>

      <div className="mt-3 h-48 overflow-auto rounded-xl border p-3 text-sm">
        {messages.length === 0 ? (
          <div className="opacity-60">
            Ask for product recommendations, sizing, etc.
          </div>
        ) : (
          <div className="flex flex-col gap-2">
            {messages.map((m, i) => (
              <div key={i} className={m.role === "user" ? "text-right" : ""}>
                <span className="inline-block rounded-lg border px-2 py-1">
                  {m.text}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="mt-3 flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          className="flex-1 rounded-xl border px-3 py-2 text-sm"
          placeholder="Ask something…"
        />
        <button onClick={send} className="rounded-xl border px-4 py-2 text-sm">
          {loading ? "…" : "Send"}
        </button>
      </div>
    </div>
  );
}
