from fastapi import APIRouter

router = APIRouter()

@router.get("/products")
def list_products(query: str | None = None, page: int = 1, limit: int = 24):
    # Placeholder until DB is wired
    return {
        "items": [],
        "page": page,
        "limit": limit,
        "query": query,
        "total": 0,
    }
