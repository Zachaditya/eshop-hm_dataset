from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, Cookie, HTTPException, Response, Request
from pydantic import BaseModel

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.core.db import get_db
from app.services.cart_service import (
    get_or_create_active_cart,
    cart_summary,
    add_item,
    set_item_quantity,
    remove_item,
    clear_cart,
)

from app.db.models import User, UserSession

from app.services.cart_service import checkout_cart

import hashlib

from datetime import datetime, timezone

router = APIRouter(prefix="/cart", tags=["cart"])

CART_COOKIE = "cart_id"
COOKIE_MAX_AGE = 60 * 60 * 24 * 30  # 30 days


# ---- Request schemas ----
class AddItemBody(BaseModel):
    product_id: str
    quantity: int = 1

class UpdateQtyBody(BaseModel):
    quantity: int


SESSION_COOKIE = "sid"

def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def get_optional_user(req: Request, db: Session) -> User | None:
    token = req.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    th = _token_hash(token)
    sess = db.query(UserSession).filter(UserSession.token_hash == th).first()
    if not sess:
        return None
    exp = sess.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if exp < datetime.now(timezone.utc):
        return None
    return db.query(User).filter(User.id == sess.user_id).first()

@router.get("")
def get_cart(
    req: Request,
    response: Response,
    db: Session = Depends(get_db),
    cart_id: Optional[str] = Cookie(default=None, alias=CART_COOKIE),
):
    user = get_optional_user(req, db)

    cart, created = get_or_create_active_cart(
        db,
        user_id=(user.id if user else None),
        cart_id=cart_id,
    )

    # Always set cookie to whatever cart you're actually using
    proto = (req.headers.get("x-forwarded-proto") or req.url.scheme).lower()
    is_https = proto == "https"

    response.set_cookie(
        key=CART_COOKIE,
        value=cart.id,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="none" if is_https else "lax",
        secure=is_https,
        path ="/",
    )

    return cart_summary(db, cart)

@router.post("/items")
def add_cart_item(
    req: Request,
    body: AddItemBody,
    response: Response,
    db: Session = Depends(get_db),
    cart_id: Optional[str] = Cookie(default=None, alias=CART_COOKIE),
):
    user = get_optional_user(req, db)
    cart, created = get_or_create_active_cart(
        db,
        user_id=(user.id if user else None),
        cart_id=cart_id,
    )
    proto = (req.headers.get("x-forwarded-proto") or req.url.scheme).lower()
    is_https = proto == "https"

    response.set_cookie(
        key=CART_COOKIE,
        value=cart.id,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="none" if is_https else "lax",
        secure=is_https,
        path ="/",
    )


    try:
        cart = add_item(db, cart.id, body.product_id, body.quantity)
    except ValueError as e:
        msg = str(e)
        raise HTTPException(status_code=404 if "not found" in msg else 400, detail=msg)
    except IntegrityError:
        # catches FK / constraint issues as a 400 instead of 500
        raise HTTPException(status_code=400, detail="Invalid cart/product reference")

    return cart_summary(db, cart)


@router.patch("/items/{item_id}")
def update_item_quantity(
    req: Request,
    item_id: str,
    body: UpdateQtyBody,
    response: Response,
    db: Session = Depends(get_db),
    cart_id: Optional[str] = Cookie(default=None, alias=CART_COOKIE),
):
    user = get_optional_user(req, db)
    cart, created = get_or_create_active_cart(
        db,
        user_id=(user.id if user else None),
        cart_id=cart_id,
    )    
    if created:
        proto = (req.headers.get("x-forwarded-proto") or req.url.scheme).lower()
        is_https = proto == "https"

        response.set_cookie(
            key=CART_COOKIE,
            value=cart.id,
            max_age=COOKIE_MAX_AGE,
            httponly=True,
            samesite="none" if is_https else "lax",
            secure=is_https,
            path ="/",
        )


    try:
        cart = set_item_quantity(db, cart.id, item_id, body.quantity)
    except ValueError as e:
        msg = str(e)
        raise HTTPException(status_code=404 if "not found" in msg else 400, detail=msg)

    return cart_summary(db, cart)


@router.delete("/items/{item_id}")
def delete_item(
    req: Request,
    item_id: str,
    response: Response,
    db: Session = Depends(get_db),
    cart_id: Optional[str] = Cookie(default=None, alias=CART_COOKIE),
):
    user = get_optional_user(req, db)
    cart, created = get_or_create_active_cart(
        db,
        user_id=(user.id if user else None),
        cart_id=cart_id,
    )
    if created:
        response.set_cookie(
            key=CART_COOKIE,
            value=cart.id,
            max_age=COOKIE_MAX_AGE,
            httponly=True,
            samesite="lax",
            secure=False,
        )

    try:
        cart = remove_item(db, cart.id, item_id)
    except ValueError as e:
        msg = str(e)
        raise HTTPException(status_code=404 if "not found" in msg else 400, detail=msg)

    return cart_summary(db, cart)


@router.post("/clear")
def clear_current_cart(
    req: Request,
    response: Response,
    db: Session = Depends(get_db),
    cart_id: Optional[str] = Cookie(default=None, alias=CART_COOKIE),
):
    user = get_optional_user(req, db)
    cart, created = get_or_create_active_cart(
        db,
        user_id=(user.id if user else None),
        cart_id=cart_id,
    )
    if created:
        response.set_cookie(
            key=CART_COOKIE,
            value=cart.id,
            max_age=COOKIE_MAX_AGE,
            httponly=True,
            samesite="lax",
            secure=False,
        )

    cart = clear_cart(db, cart.id)
    return cart_summary(db, cart)

@router.post("/checkout")
def checkout_current_cart(
    req: Request,
    response: Response,
    db: Session = Depends(get_db),
    cart_id: Optional[str] = Cookie(default=None, alias=CART_COOKIE),
):
    user = get_optional_user(req, db)
    cart, created = get_or_create_active_cart(
        db,
        user_id=(user.id if user else None),
        cart_id=cart_id,
    )
    # If we created a cart and it's empty, checkout should fail cleanly
    try:
        order_cart, new_cart = checkout_cart(db, cart)
    except ValueError as e:
        msg = str(e)
        raise HTTPException(status_code=400, detail=msg)

    # Switch cookie to the fresh active cart
    proto = (req.headers.get("x-forwarded-proto") or req.url.scheme).lower()
    is_https = proto == "https"

    response.set_cookie(
        key=CART_COOKIE,
        value=cart.id,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="none" if is_https else "lax",
        secure=is_https,
        path ="/",
    )

    order = cart_summary(db, order_cart)
    return {
        "order_id": order_cart.id,
        "order_total_quantity": order["total_quantity"],
        "order_subtotal_cents": order["subtotal_cents"],
        "cart": cart_summary(db, new_cart),
    }
