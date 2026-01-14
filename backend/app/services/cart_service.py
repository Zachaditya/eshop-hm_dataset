from __future__ import annotations

from typing import Optional, Tuple
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from uuid import uuid4

from sqlalchemy.orm import Session, joinedload

from app.db.models import Cart, CartItem, Product



ACTIVE = "active"

def _new_id() -> str:
    return uuid4().hex
def _price_cents_from_product(p: Product) -> int | None:
    # Prefer integer cents if you have it
    if getattr(p, "price_cents", None) is not None:
        return int(p.price_cents)
    # Fallback to float dollars if needed
    if getattr(p, "price", None) is not None:
        return int(round(float(p.price) * 100))
    return None


def add_item(
    db: Session,
    cart_id: str,
    product_id: str,
    quantity: int = 1,
    snapshot_unit_price: bool = True,
) -> Cart:
    """
    Add quantity of product to cart (upsert on cart_id+product_id).
    Returns the updated cart (active) with items loaded.
    """

    cart = db.query(Cart).filter(Cart.id == cart_id, Cart.status == ACTIVE).one_or_none()
    if not cart:
        raise ValueError("cart not found")

    if quantity < 1:
        raise ValueError("quantity must be >= 1")

    product = db.query(Product).filter(Product.id == product_id).one_or_none()
    if not product:
        raise ValueError("product not found")

    unit_price_cents = _price_cents_from_product(product) if snapshot_unit_price else None

    # Try to update existing row first
    item = (
        db.query(CartItem)
        .filter(CartItem.cart_id == cart_id, CartItem.product_id == product_id)
        .one_or_none()
    )

    if item:
        item.quantity += quantity
        if snapshot_unit_price and item.unit_price_cents is None and unit_price_cents is not None:
            item.unit_price_cents = unit_price_cents
        item.updated_at = datetime.utcnow()
        db.commit()
        cart = get_cart_with_items(db, cart_id)
        if not cart:
            raise ValueError("cart not found")
        return cart

    # Otherwise create new row
    item = CartItem(
        cart_id=cart_id,
        product_id=product_id,
        quantity=quantity,
        unit_price_cents=unit_price_cents if snapshot_unit_price else None,
    )
    db.add(item)
    try:
        db.commit()
    except IntegrityError:
        # In case of a race where another insert happened, retry as update
        db.rollback()
        item = (
            db.query(CartItem)
            .filter(CartItem.cart_id == cart_id, CartItem.product_id == product_id)
            .one()
        )
        item.quantity += quantity
        if snapshot_unit_price and item.unit_price_cents is None and unit_price_cents is not None:
            item.unit_price_cents = unit_price_cents
        item.updated_at = datetime.utctnow()
        db.commit()

    cart = get_cart_with_items(db, cart_id)
    if not cart:
        raise ValueError("cart not found")
    return cart

def get_cart_with_items(db: Session, cart_id: str) -> Cart | None:
    return (
        db.query(Cart)
        .options(joinedload(Cart.items))
        .filter(Cart.id == cart_id, Cart.status == ACTIVE)
        .one_or_none()
    )

def get_or_create_guest_cart(db: Session, cart_id: str | None) -> tuple[Cart, bool]:
    """
    Returns (cart, created).
    Reuses an existing guest cart if cart_id points to an ACTIVE cart with user_id NULL.
    Otherwise creates a new guest cart.
    """
    if cart_id:
        cart = (
            db.query(Cart)
            .options(joinedload(Cart.items))
            .filter(Cart.id == cart_id)
            .one_or_none()
        )
        if cart and cart.status == ACTIVE and cart.user_id is None:
            return cart, False

    # Create a brand new guest cart
    cart = Cart(user_id=None, status=ACTIVE)
    db.add(cart)
    db.commit()
    db.refresh(cart)
    return cart, True


def get_or_create_active_cart(
    db: Session,
    *,
    user_id: str | None,
    cart_id: str | None,
) -> tuple[Cart, bool]:
    """
    Returns (cart, created).
    - If user_id is present: return user's ACTIVE cart (or claim guest cart_id if provided)
    - Else: return/create guest cart
    """
    if user_id:
        # 1) Prefer user's existing active cart
        user_cart = (
            db.query(Cart)
            .options(joinedload(Cart.items))
            .filter(Cart.user_id == user_id, Cart.status == ACTIVE)
            .one_or_none()
        )
        if user_cart:
            return user_cart, False

        # 2) If there's a guest cart cookie, claim it
        if cart_id:
            guest = (
                db.query(Cart)
                .options(joinedload(Cart.items))
                .filter(Cart.id == cart_id, Cart.status == ACTIVE, Cart.user_id.is_(None))
                .one_or_none()
            )
            if guest:
                guest.user_id = user_id
                db.commit()
                db.refresh(guest)
                return guest, False

        # 3) Otherwise create a fresh user cart
        cart = Cart(user_id=user_id, status=ACTIVE)
        db.add(cart)
        db.commit()
        db.refresh(cart)
        return cart, True

    # ---- Guest flow (your existing behavior) ----
    return get_or_create_guest_cart(db, cart_id)


def attach_guest_cart_to_user(db: Session, guest_cart_id: str, user_id: str) -> Cart:
    """
    Attach the guest cart to the user.
    If the user already has an active cart, merge items into it and keep that as active.
    Returns the resulting active cart (user-owned).
    """
    guest = (
        db.query(Cart)
        .options(joinedload(Cart.items))
        .filter(Cart.id == guest_cart_id)
        .one_or_none()
    )
    if not guest or guest.status != ACTIVE or guest.user_id is not None:
        # nothing to attach
        return (
            db.query(Cart)
            .filter(Cart.user_id == user_id, Cart.status == ACTIVE)
            .one_or_none()
            or guest
        )

    # Does user already have an active cart?
    user_cart = (
        db.query(Cart)
        .options(joinedload(Cart.items))
        .filter(Cart.user_id == user_id, Cart.status == ACTIVE)
        .one_or_none()
    )

    if not user_cart:
        # Claim guest cart directly
        guest.user_id = user_id
        db.commit()
        db.refresh(guest)
        return guest

    # Merge guest items into user_cart
    # Build quick index of existing items by product_id
    existing = {i.product_id: i for i in user_cart.items}

    for gi in guest.items:
        if gi.product_id in existing:
            existing[gi.product_id].quantity += gi.quantity
        else:
            db.add(CartItem(cart_id=user_cart.id, product_id=gi.product_id, quantity=gi.quantity))

    guest.status = "merged"   
    db.commit()
    db.refresh(user_cart)
    return user_cart


def set_item_quantity(db: Session, cart_id: str, item_id: str, quantity: int) -> Cart:
    if quantity < 1:
        raise ValueError("quantity must be >= 1")

    item = (
        db.query(CartItem)
        .filter(CartItem.id == item_id, CartItem.cart_id == cart_id)
        .one_or_none()
    )
    if not item:
        raise ValueError("cart item not found")

    item.quantity = quantity
    db.commit()
    cart = get_cart_with_items(db, cart_id)
    if not cart:
        raise ValueError("cart not found")
    return cart


def remove_item(db: Session, cart_id: str, item_id: str) -> Cart:
    item = (
        db.query(CartItem)
        .filter(CartItem.id == item_id, CartItem.cart_id == cart_id)
        .one_or_none()
    )
    if not item:
        raise ValueError("cart item not found")

    db.delete(item)
    db.commit()
    cart = get_cart_with_items(db, cart_id)
    if not cart:
        raise ValueError("cart not found")
    return cart

def clear_cart(db: Session, cart_id: str) -> Cart:
    db.query(CartItem).filter(CartItem.cart_id == cart_id).delete(synchronize_session=False)
    db.commit()
    cart = get_cart_with_items(db, cart_id)
    if not cart:
        raise ValueError("cart not found")
    return cart

def cart_summary(db: Session, cart: Cart) -> dict:
    product_ids = [i.product_id for i in cart.items]
    products: dict[str, Product] = {}

    if product_ids:
        rows = db.query(Product).filter(Product.id.in_(product_ids)).all()
        products = {p.id: p for p in rows}

    items_out = []
    subtotal_cents = 0
    total_qty = 0

    for it in cart.items:
        p = products.get(it.product_id)

        # Prefer snapshot price on the item (stable), else fall back to product price
        price_cents = it.unit_price_cents
        if price_cents is None:
            if p and getattr(p, "price_cents", None) is not None:
                price_cents = int(p.price_cents)
            elif p and getattr(p, "price", None) is not None:
                price_cents = int(round(float(p.price) * 100))

        total_qty += it.quantity
        if price_cents is not None:
            subtotal_cents += price_cents * it.quantity

        items_out.append(
            {
                "id": it.id,
                "product_id": it.product_id,
                "quantity": it.quantity,
                "unit_price_cents": price_cents,
                "line_total_cents": (price_cents * it.quantity) if price_cents is not None else None,
                "product": {
                    "id": p.id if p else it.product_id,
                    "name": p.name if p else None,
                    "category": getattr(p, "category", None) if p else None,
                    "image_key": getattr(p, "image_key", None) if p else None,
                    "has_image": bool(getattr(p, "has_image", False)) if p else False,
                    "color": getattr(p, "color", None) if p else None,
                },
            }
        )

    return {
        "id": cart.id,
        "user_id": cart.user_id,
        "status": cart.status,
        "items": items_out,
        "total_quantity": total_qty,
        "subtotal_cents": subtotal_cents,
    }

def checkout_cart(db: Session, cart: Cart) -> tuple[Cart, Cart]:
    """
    Marks the current ACTIVE cart as ORDERED and creates a fresh ACTIVE cart
    (same user_id if present). Returns (ordered_cart, new_active_cart).
    """
    # cart.items should already be loaded by get_or_create_guest_cart
    if not cart.items or len(cart.items) == 0:
        raise ValueError("cart is empty")

    cart.status = "ordered"
    cart.updated_at = datetime.utcnow()
    db.add(cart)
    db.commit()
    db.refresh(cart)

    new_cart = Cart(user_id=cart.user_id, status=ACTIVE)
    db.add(new_cart)
    db.commit()
    db.refresh(new_cart)

    return cart, new_cart

