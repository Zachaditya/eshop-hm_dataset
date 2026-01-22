from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.products import router as products_router
from app.api.v1.events import router as events_router

from pathlib import Path

import random

from collections import Counter



from app.db.models import Product
from sqlalchemy import select
from app.core.db import SessionLocal


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


ALLOW_ORIGINS = (os.getenv("ALLOW_ORIGINS") or "").split(",")


app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in ALLOW_ORIGINS if o.strip()] or ["http://localhost:3000", "http://127.0.0.1:3000", "https://eshop-hm-dataset.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


HERE = Path(__file__).resolve().parent

PROJECT_ROOT = HERE if (HERE / "data").exists() else HERE.parent

IMAGE_BASE_URL = (os.getenv("IMAGE_BASE_URL") or "").rstrip("/")

IMG_ROOT = PROJECT_ROOT / "data" / "images"

if not IMAGE_BASE_URL:
    IMG_ROOT.mkdir(parents=True, exist_ok=True)
    app.mount("/images", StaticFiles(directory=str(IMG_ROOT)), name="images")


app.include_router(products_router, prefix="/v1")
app.include_router(events_router, prefix="/v1")

app.include_router(orders_router)


PRODUCTS: list[dict] = []
INDEX: dict[str, dict] = {}



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

def _coalesce(*vals, default=""):
    for v in vals:
        if v is None:
            continue
        s = str(v).strip()
        if s != "":
            return s
    return default

def _maybe_full_image_url(image_val: str, product_id: str) -> str:
    """
    DB stores:
      - a full https URL (already good)
      - a key like 'images_data/011/0110065002.jpg'
      - empty/null -> compute from article_id
    """
    v = (image_val or "").strip()
    if v.startswith("http://") or v.startswith("https://"):
        return v

    # If DB stored a key, attach IMAGE_BASE_URL.
    if v:
        return f"{IMAGE_BASE_URL}/{v.lstrip('/')}" if IMAGE_BASE_URL else v

    # If DB has nothing, compute from article_id/id
    return build_image_url(product_id)

def load_products():
    global PRODUCTS, INDEX

    items: list[dict] = []

    with SessionLocal() as db:
        stmt = select(Product)
        for p in db.execute(stmt).scalars().yield_per(2000):
            pid = str(p.id).strip()
            if not pid:
                continue

            # Prefer the "convenience" name, fall back to raw CSV name
            name = (p.name or p.prod_name or "Untitled").strip()

            # Price: prefer float `price`, else derive from `price_cents`
            price = p.price
            if price is None and p.price_cents is not None:
                price = float(p.price_cents) / 100.0
            price = float(price or 0.0)

            # Use canonical CSV columns for filtering (what your endpoints use)
            product_group_name = (p.product_group_name or p.category or "").strip()
            index_group_name = (p.index_group_name or "").strip()
            colour_group_name = (p.colour_group_name or p.color or "").strip()

            description = (p.description or p.detail_desc or "").strip()

            # Mode derived from index_group_name (same logic you had)
            mode = None
            if index_group_name == "Menswear":
                mode = "men"
            elif index_group_name in ("Ladieswear", "Divided"):
                mode = "women"

            # Image: prefer stored image_key; else compute from id (article_id)
            image_key = (p.image_key or "").strip()
            if not image_key:
                image_key = build_image_key(pid)

            # Return a usable URL (AWS in prod; local /images in dev)
            if IMAGE_BASE_URL:
                image_url = f"{IMAGE_BASE_URL}/{image_key.lstrip('/')}"
            else:
                # local fallback
                aid = pid.zfill(10)
                image_url = f"/images/{aid[:3]}/{aid}.jpg"

            items.append(
                {
                    "id": pid,
                    "name": name,
                    "price": price,
                    "image_url": image_url,

                    # fields your endpoints/search expect:
                    "product_group_name": product_group_name,
                    "index_group_name": index_group_name,
                    "colour_group_name": colour_group_name,
                    "color_name": colour_group_name,

                    "description": description,
                    "mode": mode,

                    # optional extras (handy later)
                    "perceived_colour_master_name": (p.perceived_colour_master_name or "").strip(),
                    "product_type_name": (p.product_type_name or "").strip(),
                    "has_image": bool(p.has_image),
                }
            )

    PRODUCTS = items
    INDEX = {p["id"]: p for p in PRODUCTS}

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


LOAD_ERR: str | None = None

@app.on_event("startup")
def _startup():
    global LOAD_ERR
    try:
        load_products()
        build_indices()
    except Exception as e:
        LOAD_ERR = str(e)
        PRODUCTS.clear()
        INDEX.clear()
        build_indices()



@app.get("/health")
def health():
    return {"ok": True, "products": len(PRODUCTS), "load_err": LOAD_ERR}

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
    
    try:
        hits = semantic_search_ids(q, top_k=300)
        intent = parse_query_intent(q)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Semantic search unavailable: {e}")
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

@app.get("/meta/semantic")
def semantic_meta():
    try:
        from app.search import _paths
        index_path, idmap_path, vocab_path = _paths()
        return {
            "enabled": SEMANTIC_ENABLED,
            "import_err": SEMANTIC_ERR,
            "index_exists": index_path.exists(),
            "idmap_exists": idmap_path.exists(),
            "vocab_exists": vocab_path.exists(),
            "index_path": str(index_path),
            "idmap_path": str(idmap_path),
            "vocab_path": str(vocab_path),
        }
    except Exception as e:
        return {"enabled": SEMANTIC_ENABLED, "import_err": SEMANTIC_ERR, "meta_err": str(e)}


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

