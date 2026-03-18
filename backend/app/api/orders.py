from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session as DbSession
from sqlalchemy import desc, func
from app.core.db import get_db
from app.db.models import User, Cart, CartItem, Product
from app.core.auth_utils import get_optional_user

router = APIRouter(prefix="/orders", tags=["orders"])


def require_user(req: Request, db: DbSession) -> User:
    user = get_optional_user(req, db, delete_expired=True)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user

@router.get("")
def list_orders(req: Request, db: DbSession = Depends(get_db)):
    user = require_user(req, db)

    # subtotal_cents = sum(quantity * coalesce(unit_price_cents, product.price_cents, 0))
    rows = (
        db.query(
            Cart.id.label("order_id"),
            Cart.updated_at.label("ordered_at"),
            func.coalesce(func.sum(CartItem.quantity), 0).label("quantity_purchased"),
            func.coalesce(
                func.sum(
                    CartItem.quantity
                    * func.coalesce(CartItem.unit_price_cents, Product.price_cents, 0)
                ),
                0,
            ).label("subtotal_cents"),
        )
        .join(CartItem, CartItem.cart_id == Cart.id)
        .join(Product, Product.id == CartItem.product_id)
        .filter(Cart.user_id == user.id, Cart.status == "ordered")
        .group_by(Cart.id, Cart.updated_at)
        .order_by(desc(Cart.updated_at))
        .all()
    )

    return {
        "orders": [
            {
                "order_id": r.order_id,
                "ordered_at": r.ordered_at,  # ISO string automatically via FastAPI
                "quantity_purchased": int(r.quantity_purchased or 0),
                "subtotal_cents": int(r.subtotal_cents or 0),
            }
            for r in rows
        ]
    }
