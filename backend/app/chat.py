import os
import re

from openai import AsyncOpenAI
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter()

META_MARKER = "\n\n<<HM_SHOP_PRODUCTS>>"

CHATBOT_ENABLED = os.getenv("CHATBOT_ENABLED", "false").lower() == "true"

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

DEFAULT_SYSTEM_PROMPT = """
You are HM-Shop's shopping assistant.

Rules:
- If you receive a system message that starts with "CATALOG CONTEXT" and it contains items, you MUST recommend 1–3 items from that context by name (and optionally price). Do not suggest browsing the website in that case.
- Do NOT invent products. Only use products listed in CATALOG CONTEXT.
- If CATALOG CONTEXT says "No matches found", ask exactly ONE clarifying question and suggest 2 broader keywords.
- If asked about sizing/fit, say it isn't available in this dataset.
- Be concise and friendly.
""".strip()

STOPWORDS = {
    "i", "me", "my", "you", "your", "we", "us", "a", "an", "the", "and", "or", "but",
    "help", "find", "looking", "look", "want", "need", "show", "give", "please",
    "something", "some", "any", "with", "for", "to", "of", "in", "on", "at", "from",
    "like", "that", "this", "it", "its", "catalog", "catalogue", "shop", "hm", "h&m",
    "formal", "casual", "attire", "wear", "outfit", "occasion",
}

COLOR_WORDS = {
    "black", "white", "grey", "gray", "beige", "cream", "brown", "navy", "blue", "green",
    "red", "pink", "purple", "yellow", "orange", "silver", "gold", "khaki",
}


def _tokenize(raw: str) -> list[str]:
    return [t for t in re.sub(r"[^a-z0-9\s]", " ", raw.lower()).split() if t]


def _singularize(t: str) -> str:
    return t[:-1] if t.endswith("s") and len(t) > 3 else t


def _extract_intent(raw: str) -> dict:
    toks = [_singularize(t) for t in _tokenize(raw)]
    color = next((t for t in toks if t in COLOR_WORDS), None)
    keywords = [t for t in toks if t not in STOPWORDS and t not in COLOR_WORDS]

    terms: set[str] = set(keywords[:5])
    if "jacket" in terms:
        terms.add("blazer")
        terms.add("coat")
    if "blazer" in terms:
        terms.add("jacket")
    if "coat" in terms:
        terms.add("jacket")

    return {"color": color, "terms": list(terms)[:5], "raw": raw}


def _hash32(s: str) -> int:
    h = 2166136261
    for c in s.encode():
        h ^= c
        h = (h * 16777619) & 0xFFFFFFFF
    return h


def _uniq_by_id(items: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for p in items:
        pid = str(p.get("id", ""))
        if pid not in seen:
            seen.add(pid)
            out.append(p)
    return out


def _color_match(p: dict, color: str | None) -> bool:
    if not color:
        return True
    c = str(p.get("colour_group_name") or "").lower()
    n = str(p.get("name") or "").lower()
    return color in c or color in n


def _keyword_score(p: dict, terms: list[str]) -> int:
    hay = f"{p.get('name', '')} {p.get('description', '')} {p.get('product_group_name', '')}".lower()
    return sum(2 for t in terms if t and t in hay)


def _get_products() -> list[dict]:
    from app.main import PRODUCTS  # late import — main is fully loaded before requests are served
    return PRODUCTS


def _search_products(
    q: str = "",
    limit: int = 24,
    offset: int = 0,
    mode: str | None = None,
    category: str | None = None,
    group: str | None = None,
) -> list[dict]:
    products = _get_products()
    results: list[dict] = []

    q_lower = q.strip().lower()

    for p in products:
        if mode and p.get("mode") != mode:
            continue
        if category and str(p.get("product_group_name") or "").lower() != category.lower():
            continue
        if group and str(p.get("index_group_name") or "").lower() != group.lower():
            continue
        if q_lower:
            hay = f"{p.get('name', '')} {p.get('description', '')} {p.get('product_group_name', '')} {p.get('colour_group_name', '')}".lower()
            if q_lower not in hay:
                continue
        results.append(p)

    return results[offset: offset + limit]


class ChatBody(BaseModel):
    messages: list[dict]
    mode: str | None = None
    category: str | None = None
    group: str | None = None


@router.get("/chat")
async def chat_health():
    return {"ok": True}


@router.post("/chat")
async def chat(body: ChatBody):
    if not CHATBOT_ENABLED:
        from fastapi import Response
        return Response(
            content="This chatbot demo is only available when running the project locally. "
                    "If you'd like to see a live demo, email zachaditya@berkeley.edu to schedule a demo",
            status_code=403,
        )

    incoming = body.messages
    if not incoming:
        from fastapi import Response
        return Response(content="No messages provided", status_code=400)

    messages_with_system = (
        incoming
        if incoming[0].get("role") == "system"
        else [{"role": "system", "content": DEFAULT_SYSTEM_PROMPT}] + incoming
    )

    last_user = next(
        (m["content"] for m in reversed(messages_with_system) if m.get("role") == "user"),
        "",
    )
    q_raw = last_user.strip()

    mode = body.mode
    category = body.category
    group = body.group

    ui_items: list[dict] = []
    catalog_context = ""

    if q_raw:
        intent = _extract_intent(q_raw)
        color = intent["color"]
        terms = intent["terms"]

        # Pass 1: term-by-term search
        hits: list[dict] = []
        for term in (terms if terms else [q_raw]):
            part = _search_products(q=term, limit=24, offset=0, mode=mode, category=category, group=group)
            hits.extend(part)

        hits = [p for p in _uniq_by_id(hits) if _color_match(p, color)]

        # Pass 2: color-only fallback
        if not hits and color:
            by_color = _search_products(q=color, limit=48, offset=0, mode=mode, category=category, group=group)
            garment_terms = [t for t in terms if t != color]
            hits = [
                p for p in _uniq_by_id(by_color)
                if (not garment_terms) or _keyword_score(p, garment_terms) > 0
            ]

        # Pass 3: browse fallback with hash-seeded offset
        if not hits:
            off = _hash32(f"{q_raw}|{mode or ''}|{category or ''}|{group or ''}") % 120
            hits = _search_products(q="", limit=48, offset=off, mode=mode, category=category, group=group)

        # Rerank
        ranked = sorted(
            _uniq_by_id(hits),
            key=lambda p: _keyword_score(p, terms) + (3 if color and _color_match(p, color) else 0),
            reverse=True,
        )
        ui_items = ranked[:6]

        if ui_items:
            lines = []
            for i, p in enumerate(ui_items):
                price = p.get("price")
                price_str = f"${price:.2f}" if isinstance(price, (int, float)) else "Price N/A"
                lines.append(
                    f"{i + 1}. id={p.get('id')} | name={p.get('name')} | "
                    f"group={p.get('product_group_name', '')} | "
                    f"color={p.get('colour_group_name', '')} | "
                    f"mode={p.get('mode', '')} | price={price_str}"
                )
            catalog_context = "CATALOG CONTEXT (real items; do not invent other items):\n" + "\n".join(lines)
        else:
            catalog_context = (
                f'CATALOG CONTEXT:\nNo matches found for "{q_raw}". '
                "Ask one clarifying question and suggest 2 broader keywords."
            )

    final_messages = (
        [messages_with_system[0], {"role": "system", "content": catalog_context}] + messages_with_system[1:]
        if catalog_context
        else messages_with_system
    )

    return StreamingResponse(
        _openai_stream(final_messages, ui_items),
        media_type="text/plain; charset=utf-8",
        headers={"Cache-Control": "no-store"},
    )


async def _openai_stream(messages: list[dict], ui_items: list[dict]):
    import json
    client = AsyncOpenAI()  # reads OPENAI_API_KEY from env

    try:
        async with client.chat.completions.stream(
            model=OPENAI_MODEL,
            messages=messages,  # type: ignore[arg-type]
            temperature=0.3,
            max_tokens=180,
        ) as stream:
            async for event in stream:
                delta = event.choices[0].delta.content if event.choices else None
                if delta:
                    yield delta.encode()
    except Exception as e:
        yield f"OpenAI error: {e}".encode()

    meta = json.dumps({"items": ui_items})
    yield f"{META_MARKER}{meta}".encode()
