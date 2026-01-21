from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.products import router as products_router
from app.api.v1.events import router as events_router

from pathlib import Path
import csv

import random

from collections import Counter
from fastapi.staticfiles import StaticFiles


SEMANTIC_ENABLED = False
SEMANTIC_ERR = None

try:
    from app.search import semantic_search_ids, parse_query_intent, apply_fuzzy_boosts
    SEMANTIC_ENABLED = True
except Exception as e:
    SEMANTIC_ERR = str(e)
    SEMANTIC_ENABLED = False

import secrets

from app.api.cart import router as cart_router

from app.auth import router as auth_router

from app.api.orders import router as orders_router
import os

app = FastAPI(title="HM Shop Backend", version="0.1.0")

app.include_router(cart_router)
app.include_router(auth_router)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "https://eshop-hm-dataset.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


HERE = Path(__file__).resolve().parent

PROJECT_ROOT = HERE if (HERE / "data").exists() else HERE.parent

CSV_PATH = PROJECT_ROOT / "data" / "catalog_trimmed_priced.csv"
IMAGE_BASE_URL = (os.getenv("IMAGE_BASE_URL") or "").rstrip("/")

IMG_ROOT = PROJECT_ROOT / "data" / "images"


# Serve images at /images/...
app.mount("/images", StaticFiles(directory=str(IMG_ROOT)), name="images")

app.include_router(products_router, prefix="/v1")
app.include_router(events_router, prefix="/v1")

app.include_router(orders_router)


def pick(row: dict, keys: list[str], default: str = "") -> str:
    for k in keys:
        v = row.get(k)
        if v is not None and str(v).strip() != "":
            return str(v).strip()
    return default

def to_price(v: str) -> float:
    try:
        cents = int(float(str(v).strip()))
        return cents / 100.0
    except Exception:
        return 0.0

PRODUCTS: list[dict] = []
INDEX: dict[str, dict] = {}

if IMG_ROOT.exists():
    app.mount("/images", StaticFiles(directory=str(IMG_ROOT)), name="images")


def build_image_key(article_id: str) -> str:
    aid = str(article_id).strip().zfill(10)
    # Matches your R2 layout: images_data/011/0110065002.jpg
    return f"images_data/{aid[:3]}/{aid}.jpg"

def build_image_url(article_id: str) -> str:
    key = build_image_key(article_id)
    if IMAGE_BASE_URL:
        return f"{IMAGE_BASE_URL}/{key}"
    # Local fallback (dev only)
    aid = str(article_id).strip().zfill(10)
    return f"/images/{aid[:3]}/{aid}.jpg"

def load_products():
    global PRODUCTS, INDEX
    if not CSV_PATH.exists():
        raise RuntimeError(f"CSV not found: {CSV_PATH}")

    items: list[dict] = []
    with CSV_PATH.open("r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            # IMPORTANT: images are keyed by article_id in dataset
            article_id = pick(row, ["article_id", "id", "product_id"])
            if not article_id:
                continue

            name = pick(row, ['prod_name'], default="Untitled")
            price_cents_str = pick(row, ["price_cents"], default="0")
            group_name = pick(row, ["product_group_name"], default="")
            index_group_name = pick(row, ["index_group_name"], default="")

            if index_group_name == "Menswear":
                mode = "men"
            elif index_group_name in ("Ladieswear", "Divided"):
                mode = "women"

            price = to_price(price_cents_str)

            desc = pick(row, ["detail_desc"], default="")

            color_name = pick(row, ["colour_group_name"], default="")



            item = {
                "id": str(article_id),
                "name": name,
                "price": price,
                "image_url": build_image_key(article_id),
                "product_group_name": group_name,
                "description": desc,
                "color_name": color_name,
                "colour_group_name": color_name,
                "index_group_name": index_group_name,
                "mode": mode,
            }
            items.append(item)

    PRODUCTS = items
    INDEX = {p["id"]: p for p in PRODUCTS}

load_products()

#recommend similar products using color
def norm(s: str) -> str:
    return (s or "").strip().lower()

GROUP_INDEX: dict[str, list[dict]] = {}
GROUP_COLOR_INDEX: dict[tuple[str, str], list[dict]] = {}

def build_indices():
    global GROUP_INDEX, GROUP_COLOR_INDEX
    GROUP_INDEX = {}
    GROUP_COLOR_INDEX = {}

    for p in PRODUCTS:
        g = norm(p.get("product_group_name", ""))
        c = norm(p.get("colour_group_name", ""))
        if g:
            GROUP_INDEX.setdefault(g, []).append(p)
        if g and c:
            GROUP_COLOR_INDEX.setdefault((g, c), []).append(p)

build_indices()


@app.get("/health")
def health():
    return {"ok": True, "products": len(PRODUCTS)}

# NOTE: These are currently NON-versioned (/products).
@app.get("/products")
def list_products(
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    q: str | None = None,
    index_group_name: list[str] = Query(default=[]),  
    product_group_name: list[str] = Query(default=[]),
):
    items = PRODUCTS

    # Filter by index group(s) first (Menswear / Ladieswear / Divided)
    if index_group_name:
        allowed = {s.strip().lower() for s in index_group_name}
        items = [
            p for p in items
            if str(p.get("index_group_name", "")).strip().lower() in allowed
        ]

    if product_group_name:
            allowed_groups = {s.strip().lower() for s in product_group_name}
            items = [
                p for p in items
                if str(p.get("product_group_name", "")).strip().lower() in allowed_groups
            ]

    if q:
        qq = q.lower().strip()
        items = [p for p in items if qq in p["name"].lower()]

    return {
        "items": items[offset : offset + limit],
        "total": len(items),
        "limit": limit,
        "offset": offset,
    }

@app.get("/products/homepage")
def homepage_products(
    response: Response,
    limit: int = Query(12, ge=1, le=100),
    group: str = "Garment Upper body", 
    mode: str | None = None,   
    seed: int | None = None,
):
    response.headers["Cache-Control"] = "no-store"

    target = group.strip().lower()
    m = mode.strip().lower() if mode else None

    pool = []
    for p in PRODUCTS:
        if str(p.get("product_group_name", "")).strip().lower() != target:
            continue
        if not str(p.get("image_url", "")).strip():
            continue


        g = str(p.get("index_group_name", "")).strip()
        if m == "men":
            if g and g != "Menswear":
                continue
        elif m == "women":
            if g and g not in ("Ladieswear", "Divided"):
                continue

        pool.append(p)

    if not pool:
        return {"items": [], "total": 0, "limit": limit, "group": group, "mode": mode}

    k = min(limit, len(pool))

    rng = random.Random(seed) if seed is not None else random.Random(secrets.randbits(64))
    items = rng.sample(pool, k=k) if len(pool) >= k else pool

    return {"items": items, "total": len(pool), "limit": limit, "group": group, "mode": mode}



@app.get("/products/semantic")
def semantic_products(
    q: str,
    limit: int = Query(24, ge=1, le=200),
    offset: int = Query(0, ge=0),
    index_group_name: list[str] = Query(default=[]),
    product_group_name: list[str] = Query(default=[]),
):
    if not SEMANTIC_ENABLED:
        raise HTTPException(status_code=503, detail=f"Semantic search disabled: {SEMANTIC_ERR}")
    # 1) vector retrieval
    hits = semantic_search_ids(q, top_k=300)

    # 2) hydrate
    items = []
    for pid, score in hits:
        p = INDEX.get(str(pid))
        if not p:
            continue
        p2 = dict(p)
        p2["_score"] = score
        items.append(p2)

    # 3) apply existing filters (same as /products)
    if index_group_name:
        allowed = {s.strip().lower() for s in index_group_name}
        items = [
            p for p in items
            if str(p.get("index_group_name", "")).strip().lower() in allowed
        ]

    if product_group_name:
        allowed_groups = {s.strip().lower() for s in product_group_name}
        items = [
            p for p in items
            if str(p.get("product_group_name", "")).strip().lower() in allowed_groups
        ]

    # 4) fuzzy intent boosts + rerank
    intent = parse_query_intent(q)
    items = apply_fuzzy_boosts(items, intent)

    total = len(items)
    page = items[offset : offset + limit]

    # strip internal score field if you want
    for p in page:
        p.pop("_score", None)

    return {
        "items": page,
        "total": total,
        "limit": limit,
        "offset": offset,
        "intent": intent,  # keep during dev; remove later if you want
    }


@app.get("/products/{product_id}")
def get_product(product_id: str):
    p = INDEX.get(str(product_id))
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    return p

@app.get("/products/{product_id}/similar")
def similar_products(
    product_id: str,
    limit: int = Query(8, ge=1, le=50),
    seed: int | None = None,
):
    base = INDEX.get(str(product_id))
    if not base:
        raise HTTPException(status_code=404, detail="Product not found")

    g = norm(base.get("product_group_name", ""))
    c = norm(base.get("colour_group_name", ""))

    rng = random.Random(seed) if seed is not None else random

    # Primary: same group + color
    primary_pool = GROUP_COLOR_INDEX.get((g, c), [])
    primary = [p for p in primary_pool if p["id"] != str(product_id)]

    # Secondary: same group (different colors)
    group_pool = GROUP_INDEX.get(g, [])
    secondary = [p for p in group_pool if p["id"] != str(product_id)]

    # Dedup while keeping order
    seen = set()
    primary = [p for p in primary if not (p["id"] in seen or seen.add(p["id"]))]
    secondary = [p for p in secondary if not (p["id"] in seen or seen.add(p["id"]))]

    # Choose some from primary, then fill from secondary
    take_primary = min(len(primary), max(0, int(limit * 0.6)))
    chosen = []

    if primary:
        chosen += rng.sample(primary, k=min(take_primary, len(primary)))

    remaining = limit - len(chosen)
    if remaining > 0 and secondary:
        # avoid picking already chosen
        chosen_ids = {p["id"] for p in chosen}
        secondary2 = [p for p in secondary if p["id"] not in chosen_ids]
        chosen += rng.sample(secondary2, k=min(remaining, len(secondary2)))

    return {
        "base_id": product_id,
        "group": base.get("product_group_name", ""),
        "color": base.get("colour_group_name", ""),
        "items": chosen,
    }

@app.get("/meta/product-groups")
def product_groups():
    # counts by index_group_name (Menswear/Ladieswear/Divided)
    by_mode: dict[str, Counter] = {}
    for p in PRODUCTS:
        m = str(p.get("index_group_name", "")).strip() or "UNKNOWN"
        g = str(p.get("product_group_name", "")).strip() or "UNKNOWN"
        by_mode.setdefault(m, Counter())[g] += 1

    return {
        m: [{"group": g, "count": c} for g, c in by_mode[m].most_common()]
        for m in by_mode
    }

