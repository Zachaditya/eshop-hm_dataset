from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session as DbSession
from sqlalchemy import desc, func
from app.core.db import get_db
from app.db.models import User, UserSession, Cart, CartItem, Product
from datetime import datetime, timezone
import hashlib

router = APIRouter(prefix="/orders", tags=["orders"])
SESSION_COOKIE = "sid"

def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def require_user(req: Request, db: DbSession) -> User:
    token = req.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    th = _token_hash(token)
    sess = db.query(UserSession).filter(UserSession.token_hash == th).first()
    if not sess:
        raise HTTPException(status_code=401, detail="Not authenticated")

    exp = sess.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)

    if exp < datetime.now(timezone.utc):
        # optional cleanup
        db.delete(sess)
        db.commit()
        raise HTTPException(status_code=401, detail="Session expired")

    user = db.query(User).filter(User.id == sess.user_id).first()
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
