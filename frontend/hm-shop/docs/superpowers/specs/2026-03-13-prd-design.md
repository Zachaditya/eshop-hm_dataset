# Product Requirements Document — ESHOP (H&M Catalog)

**Date:** 2026-03-13
**Status:** Active
**Audience:** Development reference + recruiter/portfolio showcase

---

## 1. Overview & Problem Statement

**Product Name:** ESHOP (H&M Catalog)

**One-liner:** A full-stack e-commerce storefront powered by the H&M product dataset, featuring a privacy-first AI shopping assistant that runs entirely on-device.

**Problem:** Discovering relevant clothing in a large catalog is tedious. Users typically rely on keyword search, which fails when they describe what they want conversationally ("something casual and navy for a dinner"). Traditional product search ignores intent, color, and occasion context.

**Solution:** An AI assistant that understands natural language queries, extracts intent (garment type, color, occasion), retrieves real catalog matches, grounds the LLM response in those results, and streams product recommendations alongside the conversational reply — all without sending user data to any external API.

**Users:**
- **Primary:** Fashion shoppers who prefer conversational discovery over filter-heavy browsing
- **Secondary:** Developers and recruiters evaluating the technical implementation

---

## 2. Features & User Flows

### Core Features

| Feature | Description |
|---|---|
| Product catalog | Browse Men/Women across Clothing, Footwear, Accessories, Lifestyle with dropdown subcategories |
| Search | Keyword search scoped to current mode/category, persists filters across navigation |
| Product detail | Individual product page with image, price, color, group |
| Cart | Add/remove items, update quantities, persistent via cookie session |
| Checkout | Single-step checkout, creates order record |
| Auth | Register, login, logout — cookie-based session, guest cart merges on login |
| AI Assistant | Floating chat widget (or full `/chatbot` page); natural language → product recommendations |
| Recommendations | Homepage surfaces curated upper-body and footwear picks |
| Events | API-backed promotional events/banners |

### Key User Flows

1. **Browse → Add to Cart → Checkout** — standard e-commerce funnel
2. **Search** — user types in navbar, lands on `/search` with filtered results
3. **AI Discovery** — user opens chat widget, describes what they want, gets streamed reply + product cards they can click through to PDP
4. **Auth** — register/login, account page, cart persists across sessions

---

## 3. AI Assistant — Technical Design

The AI assistant is the core differentiator of this project: a privacy-first, fully local shopping assistant with keyword retrieval + catalog grounding, streaming responses, and zero external API calls.

### Pipeline

```
User message
    → Intent extraction (tokenize → stopword filter → singularize → color detection → synonym expansion)
    → Multi-pass product retrieval (term-by-term → color fallback → hash-seeded browse fallback)
    → Reranking (keyword score + color match)
    → Catalog context injection (system message grounding the LLM)
    → Ollama (phi3:mini, local) streaming response
    → Stream parsing (text tokens + metadata split on <<HM_SHOP_PRODUCTS>> marker)
    → Client renders streamed text + product cards simultaneously
```

### Key Design Decisions

**No external LLM calls**
Ollama runs locally (`phi3:mini` default, `temperature: 0.3`, `num_ctx: 1024`, `num_predict: 180`). Zero data egress, demo-safe, no API costs. Low temperature and tight context window are deliberate — they reduce hallucination and keep responses faithful to the grounded catalog context. The chatbot is gated by `NEXT_PUBLIC_CHATBOT_ENABLED` and disabled in production since Ollama requires local hardware.

**Deterministic retrieval before generation**
Products are fetched via the existing `/api/products` route before the LLM is called. The model is grounded in real catalog items and cannot hallucinate products. This is keyword retrieval + catalog grounding, not embedding-based RAG — a deliberate choice for speed, determinism, and zero infrastructure overhead.

**Multi-pass retrieval with fallbacks**
Searches term-by-term (more forgiving than a full-sentence query). Falls back to color-only search if terms yield no results. Final fallback: a `hash32(query)` seeds a deterministic offset into the catalog browse — different queries get different fallback sets rather than always returning page 0.

**Garment synonym expansion**
`extractIntent()` expands common synonyms at query time: `jacket → [blazer, coat]`, `blazer → [jacket]`, etc. This improves recall without requiring a vector index.

**Streaming protocol**
The server streams raw text tokens to the client. A `<<HM_SHOP_PRODUCTS>>` sentinel appended at end carries product JSON. The client's `readAgentStream()` detects the marker across chunk boundaries in a single pass — product cards appear as soon as the stream closes, no second request needed.

**Catalog grounding via system message injection**
Matched products are injected as a `CATALOG CONTEXT` system message between the main system prompt and the conversation history. The model is instructed to only recommend items from this context, preventing hallucination.

### API Routes

| Route | Method | Purpose |
|---|---|---|
| `/api/agent` | `POST` | Main AI assistant endpoint — retrieval + Ollama streaming |
| `/api/products` | `GET` | Product search/browse, proxied to backend with session header |
| `/api/recommendations` | `GET` | Personalized product recommendations |
| `/api/events` | `GET` | Promotional events/banners |

---

## 4. Roadmap

### Now (current)
- Full browse, search, cart, checkout, auth flows
- AI assistant with local LLM + keyword retrieval + catalog grounding
- Session-based personalization (guest + authenticated)

### Known Issues
- `NEXT_PUBLIC_CHATBOT_ENABLED` env var check is inverted in `src/app/api/agent/route.ts` — set to `"false"` to enable locally (counterintuitive; fix before production)
- Order history UI is not yet built (`src/lib/orders.ts` exists but no page)
- Chat product card images bypass the `resolveImageUrl()` utility used elsewhere

### Next (planned)
- **Personalization** — user preference profiles, purchase history-based recommendations, "because you bought X" shelf on homepage
- Recommendation model trained on H&M dataset interaction signals
- Per-user saved items / wishlist

### Later (stretch)
- Swap Ollama for hosted model (Claude API) for production chatbot availability
- Semantic/vector search to replace keyword scoring
- Order history page, email receipts
- Mobile-optimized layout / PWA

---

## 5. Success Metrics

| Metric | Description |
|---|---|
| AI assistant engagement | % of sessions that use the chat widget |
| Chat-to-PDP conversion | % of chat sessions that result in a product page visit |
| Cart conversion | % of sessions that add at least one item |
| Checkout completion | % of carts that complete checkout |
| Search relevance | % of searches that return ≥1 result |

---

## 6. Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 15 (App Router), TypeScript, Tailwind CSS |
| UI primitives | Lucide icons, Framer Motion |
| AI runtime | Ollama (local), `phi3:mini` default |
| Backend API | External service via `API_BASE_URL` env var |
| Auth | Cookie-based sessions, `/auth/*` endpoints |
| Cart | Cookie-persisted, server-side cart ID |
| Deployment | Live demo + portfolio site embed |
