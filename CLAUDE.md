# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

An H&M-style e-commerce shop with a FastAPI backend and Next.js 16 frontend. The dataset is based on the H&M fashion catalog.

## Dev Commands

### Backend (run from `backend/`)
```bash
# Install dependencies
pip install -r requirements.txt

# Start dev server
uvicorn app.main:app --reload

# Run migrations
alembic upgrade head

# Seed product data from CSV
python -m scripts.seed_products

# Build FAISS semantic search index (must run after seeding)
python -m scripts.build_semantic_index
```

### Frontend (run from `frontend/hm-shop/`)
```bash
npm install
npm run dev      # http://localhost:3000
npm run build
npm run lint     # eslint
```

## Architecture

### Backend (`backend/app/`)

**Data flow**: Products are seeded from `data/catalog_trimmed_priced.csv` into SQLite (`app.db`). On startup, `main.py` loads all products into an in-memory `PRODUCTS` list and `INDEX` dict for fast filtering. Semantic search (`FAISS + sentence-transformers/all-MiniLM-L6-v2`) is optional and lazy-loaded — if the index files don't exist at `data/semantic/`, `SEMANTIC_ENABLED` is set to `False` and only keyword search works.

**Key env vars** (`backend/.env`):
- `DATABASE_URL` — defaults to `sqlite:///./app.db`
- `IMAGE_BASE_URL` — Cloudflare R2 base URL for product images; if unset, images are served locally from `data/images/`
- `ALLOW_ORIGINS` — comma-separated CORS origins

**Router layout**:
- `app.main` — product endpoints: `GET /products`, `GET /products/semantic`, `GET /products/{id}`, `GET /products/{id}/recommendations`
- `app.auth` — `POST /auth/register`, `POST /auth/login`, `POST /auth/logout`, `GET /auth/me` (prefix `/auth`)
- `app.api.cart` — cart CRUD (cookie-based cart_id)
- `app.api.orders` — order listing
- `app.api.v1.events` — event tracking (prefix `/v1`)

**Auth**: Passwordless (email-only). Sessions stored in `UserSession` table, hashed token in an httponly cookie (`session`). Use `get_optional_user(req, db)` from `app.core.auth_utils` everywhere — never inline the token hash logic. Pass `delete_expired=True` only in auth routes.

**Image URL resolution**: The DB `image_key` field stores either a full `https://` URL, a storage key like `images_data/011/0110065002.jpg`, or is empty. Always use `_maybe_full_image_url(image_key, product_id)` in backend and `resolveImageUrl(imageUrl)` from `frontend/.../lib/api.ts` in frontend.

**Cart**: Always use `_set_cart_cookie(response, req, cart_id)` from `app.api.cart` — it handles HTTPS detection for the `secure` flag.

### Frontend (`frontend/hm-shop/src/`)

**Framework**: Next.js 16 (App Router), React 19, Tailwind CSS v4, Framer Motion.

**API calls**: All backend calls go through `lib/api.ts` using `backendFetch()`. `NEXT_PUBLIC_API_BASE` env var controls the backend URL (defaults to `http://localhost:3000` — set to `http://localhost:8000` for local dev).

**Types**: Always import `Product`, `Event`, `Recommendation` from `@/lib/types` — never redefine them locally.

**Route structure**: Category pages like `/men/clothing`, `/women/accessories` etc. render `ProductCatalog` with appropriate filter params. `/search` renders `SearchResultsPage` with infinite scroll. `/products/[id]` is the product detail page.

**Key components**:
- `ProductCatalog` — animated grid with filtering, fetches via `fetchProducts(endpoint, opts)`
- `SearchResultsPage` — infinite scroll search UI, handles both keyword and semantic results
- `Navbar` — global nav with search (guards against empty query)

### Database Migrations

Managed with Alembic. Migration files are in `backend/alembic/versions/`. After changing `app/db/models.py`, generate a new migration:
```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
```

### Semantic Search Setup

Requires running `build_semantic_index.py` which reads `data/catalog_trimmed_priced.csv` and writes three files to `data/semantic/`: `faiss.index`, `id_map.json`, `vocab.json`. The backend silently disables semantic search if these files are missing.
