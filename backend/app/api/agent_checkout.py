"""Agent checkout API for merchant-side order creation and payment verification."""

from __future__ import annotations

import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.db import get_db
from app.db.models import Cart, PaymentIntent, User
from app.services.cart_service import add_item, cart_summary, get_or_create_guest_cart
from app.services.onchain import amount_cents_to_usdc_base_units, verify_usdc_transfer


router = APIRouter(prefix="/agent", tags=["agent-checkout"])

REQUIRES_PAYMENT = "requires_payment"
PAID = "paid"
CANCELED = "canceled"
NETWORK = "base-sepolia"
CURRENCY = "USDC"


class AgentOrderIn(BaseModel):
    """Request body for creating an agent checkout order."""

    product_id: str = Field(..., min_length=1)


class ConfirmPaymentIn(BaseModel):
    """Request body for confirming a payment intent by transaction hash."""

    tx_hash: str = Field(..., min_length=1)


def _payment_not_verified(message: str) -> HTTPException:
    """
    Build the standard failed-payment API error.

    Params:
        message: Human-readable explanation of the failed verification.

    Returns:
        An HTTPException using the Phase 4 PAYMENT_NOT_VERIFIED code.
    """
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={"code": "PAYMENT_NOT_VERIFIED", "message": message},
    )


def _utcnow() -> datetime:
    """
    Return a UTC timestamp compatible with the existing naive DateTime columns.

    Params:
        None.

    Returns:
        Current UTC time with timezone info stripped for this schema's DateTime
        columns.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def require_agent_key(x_agent_key: str | None = Header(default=None, alias="X-Agent-Key")) -> None:
    """
    Require the shared agent API key on every merchant checkout route.

    Params:
        x_agent_key: Incoming X-Agent-Key request header.

    Returns:
        None when the configured shared secret matches the request header.
    """
    expected = settings.agent_api_key
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AGENT_API_KEY_NOT_CONFIGURED",
        )
    if not x_agent_key or not secrets.compare_digest(x_agent_key, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="UNAUTHORIZED_AGENT")


def _configured_demo_email() -> str:
    """
    Return the normalized demo user email required for paid agent orders.

    Params:
        None.

    Returns:
        Lowercase configured demo user email.
    """
    email = (settings.agent_demo_user_email or "").strip().lower()
    if not email:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AGENT_DEMO_USER_EMAIL_NOT_CONFIGURED",
        )
    return email


def _get_or_create_demo_user(db: Session) -> User:
    """
    Load or create the demo user that owns verified agent checkout orders.

    Params:
        db: SQLAlchemy session used for the current request.

    Returns:
        User row matching AGENT_DEMO_USER_EMAIL.
    """
    email = _configured_demo_email()
    user = db.query(User).filter(User.email == email).one_or_none()
    if user:
        return user

    user = User(email=email, name="Agent Demo User", password_hash=secrets.token_hex(32))
    db.add(user)
    db.flush()
    return user


def _load_intent(db: Session, payment_intent_id: str) -> PaymentIntent:
    """
    Load a payment intent with its cart or raise a 404 API error.

    Params:
        db: SQLAlchemy session used for the current request.
        payment_intent_id: Payment intent identifier from the route path.

    Returns:
        PaymentIntent row with the related Cart eagerly loaded.
    """
    intent = (
        db.query(PaymentIntent)
        .options(joinedload(PaymentIntent.cart))
        .filter(PaymentIntent.id == payment_intent_id)
        .one_or_none()
    )
    if not intent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PAYMENT_INTENT_NOT_FOUND")
    return intent


def _normalize_tx_hash(tx_hash: str) -> str:
    """
    Normalize a transaction hash for replay checks and persistence.

    Params:
        tx_hash: Raw transaction hash supplied by the caller.

    Returns:
        Stripped lowercase transaction hash.
    """
    return tx_hash.strip().lower()


def _paid_order_response(intent: PaymentIntent) -> dict:
    """
    Serialize a paid payment intent as the agent checkout order response.

    Params:
        intent: Paid PaymentIntent row.

    Returns:
        JSON-serializable order details for the agent caller.
    """
    return {
        "order_id": intent.cart_id,
        "payment_intent_id": intent.id,
        "amount_cents": intent.amount_cents,
        "pay_to": intent.pay_to,
        "currency": CURRENCY,
        "network": NETWORK,
        "status": intent.status,
        "tx_hash": intent.tx_hash,
    }


@router.post("/orders", dependencies=[Depends(require_agent_key)])
def create_agent_order(body: AgentOrderIn, db: Session = Depends(get_db)) -> dict:
    """
    Create a one-item guest cart and payment intent for an agent purchase.

    Params:
        body: Product identifier selected by the agent caller.
        db: SQLAlchemy session used for cart and payment-intent writes.

    Returns:
        Order and payment-intent details including cart-derived amount and the
        configured merchant recipient.
    """
    cart, _created = get_or_create_guest_cart(db, None)
    try:
        cart = add_item(db, cart.id, body.product_id, quantity=1, snapshot_unit_price=True)
    except ValueError as exc:
        message = str(exc)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if "not found" in message else status.HTTP_400_BAD_REQUEST,
            detail=message,
        )

    summary = cart_summary(db, cart)
    amount_cents = int(summary["subtotal_cents"])
    if amount_cents <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="PRODUCT_PRICE_UNAVAILABLE")

    intent = PaymentIntent(
        cart_id=cart.id,
        amount_cents=amount_cents,
        pay_to=settings.merchant_pay_to_address,
        status=REQUIRES_PAYMENT,
    )
    db.add(intent)
    db.commit()
    db.refresh(intent)

    return {
        "order_id": cart.id,
        "payment_intent_id": intent.id,
        "amount_cents": amount_cents,
        "pay_to": intent.pay_to,
        "currency": CURRENCY,
        "network": NETWORK,
        "status": intent.status,
    }


@router.post("/payment-intents/{payment_intent_id}/cancel", dependencies=[Depends(require_agent_key)])
def cancel_payment_intent(payment_intent_id: str, db: Session = Depends(get_db)) -> dict:
    """
    Cancel an unpaid payment intent and retire its unpaid cart.

    Params:
        payment_intent_id: Payment intent identifier from the route path.
        db: SQLAlchemy session used for intent and cart updates.

    Returns:
        Current payment-intent status and a reason when the intent was already
        paid before cancellation.
    """
    intent = _load_intent(db, payment_intent_id)
    if intent.status == PAID:
        response = _paid_order_response(intent)
        response["reason_code"] = "ALREADY_PAID"
        return response

    if intent.status != CANCELED:
        intent.status = CANCELED
        if intent.cart and intent.cart.status == "active":
            intent.cart.status = "abandoned"
            intent.cart.updated_at = _utcnow()
        db.commit()
        db.refresh(intent)

    return {"payment_intent_id": intent.id, "order_id": intent.cart_id, "status": intent.status}


@router.post("/payment-intents/{payment_intent_id}/confirm", dependencies=[Depends(require_agent_key)])
def confirm_payment_intent(
    payment_intent_id: str,
    body: ConfirmPaymentIn,
    db: Session = Depends(get_db),
) -> dict:
    """
    Verify a USDC transfer and finalize its cart as a paid demo-user order.

    Params:
        payment_intent_id: Payment intent identifier from the route path.
        body: Transaction hash supplied by the agent after it sends USDC.
        db: SQLAlchemy session used for verification side effects.

    Returns:
        Paid order details when the transaction proves exact payment.
    """
    intent = _load_intent(db, payment_intent_id)
    tx_hash = _normalize_tx_hash(body.tx_hash)

    if intent.status == PAID:
        if _normalize_tx_hash(intent.tx_hash or "") == tx_hash:
            return _paid_order_response(intent)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="PAYMENT_INTENT_ALREADY_PAID")

    if intent.status == CANCELED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="PAYMENT_INTENT_CANCELED")

    existing = (
        db.query(PaymentIntent)
        .filter(PaymentIntent.tx_hash == tx_hash, PaymentIntent.id != intent.id)
        .one_or_none()
    )
    if existing:
        raise _payment_not_verified("Transaction hash has already been used for another order.")

    verification = verify_usdc_transfer(
        tx_hash,
        rpc_url=settings.base_sepolia_rpc_url,
        usdc_contract_address=settings.usdc_contract_address,
        pay_to=intent.pay_to,
        amount_base_units=amount_cents_to_usdc_base_units(intent.amount_cents),
    )
    if not verification.verified:
        raise _payment_not_verified(verification.message)

    demo_user = _get_or_create_demo_user(db)
    if not intent.cart:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="ORDER_CART_NOT_FOUND")

    intent.status = PAID
    intent.tx_hash = tx_hash
    intent.paid_at = _utcnow()
    intent.cart.user_id = demo_user.id
    intent.cart.status = "ordered"
    intent.cart.updated_at = _utcnow()

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise _payment_not_verified("Transaction hash has already been used for another order.")

    db.refresh(intent)
    return _paid_order_response(intent)
