"""Tests for merchant-side agent checkout and payment verification."""

from __future__ import annotations

import os
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:////private/tmp/eshop_agent_checkout_test.sqlite"
os.environ["AGENT_API_KEY"] = "test-agent-key"
os.environ["MERCHANT_PAY_TO_ADDRESS"] = "0xa7BD909D765d9e93f75a0d76E77827a6EdC8A69D"
os.environ["BASE_SEPOLIA_RPC_URL"] = "https://sepolia.base.org"
os.environ["USDC_CONTRACT_ADDRESS"] = "0x036CbD53842c5426634e7929541eC2318f3dCF7e"
os.environ["AGENT_DEMO_USER_EMAIL"] = "agent-demo@example.com"

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError
from sqlalchemy.schema import CreateIndex
from sqlalchemy.orm import Session

from app.api.agent_checkout import router as agent_checkout_router
from app.auth import router as auth_router
from app.api.orders import router as orders_router
from app.core.db import Base, SessionLocal, engine
from app.db.models import Cart, PaymentIntent, Product, User
from app.services.onchain import (
    PaymentVerification,
    TRANSFER_TOPIC,
    amount_cents_to_usdc_base_units,
    receipt_has_exact_usdc_transfer,
)


TEST_DB_PATH = Path("/private/tmp/eshop_agent_checkout_test.sqlite")
AGENT_HEADERS = {"X-Agent-Key": "test-agent-key"}
MERCHANT = "0xa7BD909D765d9e93f75a0d76E77827a6EdC8A69D"
USDC = "0x036CbD53842c5426634e7929541eC2318f3dCF7e"
SHOPPER = "0x1111111111111111111111111111111111111111"


def _topic_for_address(address: str) -> str:
    """
    Encode an EVM address as a 32-byte indexed event topic.

    Params:
        address: Hex EVM address.

    Returns:
        0x-prefixed event topic with the address left-padded to 32 bytes.
    """
    return "0x" + address.lower().removeprefix("0x").rjust(64, "0")


def _transfer_receipt(*, to: str = MERCHANT, value: int = 11_000_000, status: int = 1) -> dict:
    """
    Build a minimal ERC-20 Transfer receipt fixture.

    Params:
        to: Recipient address encoded in the Transfer log.
        value: Transfer value encoded in USDC base units.
        status: Transaction receipt status value.

    Returns:
        Receipt-like dictionary consumed by receipt_has_exact_usdc_transfer().
    """
    return {
        "status": status,
        "logs": [
            {
                "address": USDC,
                "topics": [TRANSFER_TOPIC, _topic_for_address(SHOPPER), _topic_for_address(to)],
                "data": hex(value),
            }
        ],
    }


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """
    Create an isolated FastAPI test client backed by a fresh SQLite schema.

    Params:
        monkeypatch: Pytest monkeypatch fixture used to replace chain reads.

    Returns:
        TestClient with agent, auth, and orders routers installed.
    """
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        db.add(
            Product(
                id="0493438021",
                name="ROOT CLASSIC TEE",
                category="Garment Upper body",
                price=11.0,
                price_cents=1100,
                currency="USD",
            )
        )
        db.commit()

    def fake_verify(tx_hash: str, **kwargs: object) -> PaymentVerification:
        """
        Replace RPC verification with deterministic test receipts.

        Params:
            tx_hash: Transaction hash supplied to the confirm endpoint.
            **kwargs: Verification arguments from the route under test.

        Returns:
            PaymentVerification generated from a matching or intentionally bad
            receipt fixture.
        """
        if tx_hash in {"0xgood", "0xsecondgood"}:
            return receipt_has_exact_usdc_transfer(
                _transfer_receipt(value=amount_cents_to_usdc_base_units(1100)),
                usdc_contract_address=str(kwargs["usdc_contract_address"]),
                pay_to=str(kwargs["pay_to"]),
                amount_base_units=int(kwargs["amount_base_units"]),
            )
        if tx_hash == "0xwrongamount":
            return receipt_has_exact_usdc_transfer(
                _transfer_receipt(value=10_000),
                usdc_contract_address=str(kwargs["usdc_contract_address"]),
                pay_to=str(kwargs["pay_to"]),
                amount_base_units=int(kwargs["amount_base_units"]),
            )
        if tx_hash == "0xwrongrecipient":
            return receipt_has_exact_usdc_transfer(
                _transfer_receipt(to="0x2222222222222222222222222222222222222222"),
                usdc_contract_address=str(kwargs["usdc_contract_address"]),
                pay_to=str(kwargs["pay_to"]),
                amount_base_units=int(kwargs["amount_base_units"]),
            )
        return PaymentVerification(False, "RECEIPT_NOT_FOUND", "Transaction receipt was not found.")

    monkeypatch.setattr("app.api.agent_checkout.verify_usdc_transfer", fake_verify)

    app = FastAPI()
    app.include_router(agent_checkout_router)
    app.include_router(auth_router)
    app.include_router(orders_router)
    return TestClient(app)


def _create_order(client: TestClient) -> dict:
    """
    Create a valid agent checkout order through the test client.

    Params:
        client: TestClient configured by the client fixture.

    Returns:
        JSON response from POST /agent/orders.
    """
    response = client.post("/agent/orders", headers=AGENT_HEADERS, json={"product_id": "0493438021"})
    assert response.status_code == 200
    return response.json()


def test_agent_routes_require_api_key(client: TestClient) -> None:
    """
    Verify every agent checkout route rejects missing or wrong shared secrets.

    Params:
        client: TestClient configured by the client fixture.

    Returns:
        None. Assertions prove unauthorized requests fail before route effects.
    """
    endpoints = [
        ("/agent/orders", {"product_id": "0493438021"}),
        ("/agent/payment-intents/missing/confirm", {"tx_hash": "0xgood"}),
        ("/agent/payment-intents/missing/cancel", {}),
    ]
    for path, body in endpoints:
        assert client.post(path, json=body).status_code == 401
        assert client.post(path, headers={"X-Agent-Key": "wrong"}, json=body).status_code == 401


def test_create_order_uses_cart_price_and_configured_recipient(client: TestClient) -> None:
    """
    Verify order creation snapshots the product price and merchant recipient.

    Params:
        client: TestClient configured by the client fixture.

    Returns:
        None. Assertions inspect both the API response and persisted intent/cart.
    """
    payload = _create_order(client)

    assert payload["amount_cents"] == 1100
    assert payload["pay_to"] == MERCHANT
    assert payload["currency"] == "USDC"
    assert payload["network"] == "base-sepolia"
    assert payload["status"] == "requires_payment"

    with SessionLocal() as db:
        intent = db.get(PaymentIntent, payload["payment_intent_id"])
        cart = db.get(Cart, payload["order_id"])
        assert intent is not None
        assert intent.amount_cents == 1100
        assert intent.pay_to == MERCHANT
        assert cart is not None
        assert cart.status == "active"
        assert cart.items[0].unit_price_cents == 1100


def test_cancel_only_cancels_unpaid_intents(client: TestClient) -> None:
    """
    Verify cancellation retires unpaid carts and leaves paid intents unchanged.

    Params:
        client: TestClient configured by the client fixture.

    Returns:
        None. Assertions cover unpaid cancellation and paid cancellation response.
    """
    payload = _create_order(client)
    intent_id = payload["payment_intent_id"]

    cancel = client.post(f"/agent/payment-intents/{intent_id}/cancel", headers=AGENT_HEADERS)
    assert cancel.status_code == 200
    assert cancel.json()["status"] == "canceled"

    with SessionLocal() as db:
        intent = db.get(PaymentIntent, intent_id)
        cart = db.get(Cart, payload["order_id"])
        assert intent is not None
        assert intent.status == "canceled"
        assert cart is not None
        assert cart.status == "abandoned"

    paid = _create_order(client)
    paid_intent_id = paid["payment_intent_id"]
    confirm = client.post(
        f"/agent/payment-intents/{paid_intent_id}/confirm",
        headers=AGENT_HEADERS,
        json={"tx_hash": "0xgood"},
    )
    assert confirm.status_code == 200

    cancel_paid = client.post(f"/agent/payment-intents/{paid_intent_id}/cancel", headers=AGENT_HEADERS)
    assert cancel_paid.status_code == 200
    assert cancel_paid.json()["status"] == "paid"
    assert cancel_paid.json()["reason_code"] == "ALREADY_PAID"


@pytest.mark.parametrize("tx_hash", ["0xfake", "0xwrongamount", "0xwrongrecipient"])
def test_confirm_rejects_unverified_payments(client: TestClient, tx_hash: str) -> None:
    """
    Verify fake hashes, wrong amounts, and wrong recipients cannot pay an order.

    Params:
        client: TestClient configured by the client fixture.
        tx_hash: Hash routed to the fake verifier scenario.

    Returns:
        None. Assertions prove the intent and cart remain unpaid.
    """
    payload = _create_order(client)
    response = client.post(
        f"/agent/payment-intents/{payload['payment_intent_id']}/confirm",
        headers=AGENT_HEADERS,
        json={"tx_hash": tx_hash},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "PAYMENT_NOT_VERIFIED"

    with SessionLocal() as db:
        intent = db.get(PaymentIntent, payload["payment_intent_id"])
        cart = db.get(Cart, payload["order_id"])
        assert intent is not None
        assert intent.status == "requires_payment"
        assert intent.tx_hash is None
        assert cart is not None
        assert cart.status == "active"


def test_confirm_paid_order_is_idempotent_and_visible_to_demo_user(client: TestClient) -> None:
    """
    Verify exact payment marks the order paid once and exposes it in order history.

    Params:
        client: TestClient configured by the client fixture.

    Returns:
        None. Assertions cover idempotent confirmation and demo account visibility.
    """
    payload = _create_order(client)
    intent_id = payload["payment_intent_id"]
    body = {"tx_hash": "0xgood"}

    first = client.post(f"/agent/payment-intents/{intent_id}/confirm", headers=AGENT_HEADERS, json=body)
    second = client.post(f"/agent/payment-intents/{intent_id}/confirm", headers=AGENT_HEADERS, json=body)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert first.json()["status"] == "paid"
    assert first.json()["order_id"] == payload["order_id"]
    assert first.json()["tx_hash"] == "0xgood"

    login = client.post("/auth/login", json={"email": "agent-demo@example.com"})
    assert login.status_code == 200
    orders = client.get("/orders")
    assert orders.status_code == 200
    assert orders.json()["orders"] == [
        {
            "order_id": payload["order_id"],
            "ordered_at": orders.json()["orders"][0]["ordered_at"],
            "quantity_purchased": 1,
            "subtotal_cents": 1100,
        }
    ]

    with SessionLocal() as db:
        ordered_count = db.query(Cart).filter(Cart.status == "ordered").count()
        assert ordered_count == 1


def test_confirm_rejects_hash_replay_for_another_intent(client: TestClient) -> None:
    """
    Verify a transaction hash paid on one intent cannot pay a second intent.

    Params:
        client: TestClient configured by the client fixture.

    Returns:
        None. Assertions prove replay protection runs before another payment is marked paid.
    """
    first = _create_order(client)
    second = _create_order(client)

    paid = client.post(
        f"/agent/payment-intents/{first['payment_intent_id']}/confirm",
        headers=AGENT_HEADERS,
        json={"tx_hash": "0xgood"},
    )
    assert paid.status_code == 200

    replay = client.post(
        f"/agent/payment-intents/{second['payment_intent_id']}/confirm",
        headers=AGENT_HEADERS,
        json={"tx_hash": "0xgood"},
    )
    assert replay.status_code == 400
    assert replay.json()["detail"]["code"] == "PAYMENT_NOT_VERIFIED"

    with SessionLocal() as db:
        second_intent = db.get(PaymentIntent, second["payment_intent_id"])
        assert second_intent is not None
        assert second_intent.status == "requires_payment"


def test_active_cart_index_is_partial_on_postgresql() -> None:
    """Restrict PostgreSQL's unique cart index to active carts only.

    Params:
        None.

    Returns:
        None. Compiled production DDL permits multiple historical orders per user.
    """
    index = next(index for index in Cart.__table__.indexes if index.name == "ux_carts_one_active_per_user")
    ddl = str(CreateIndex(index).compile(dialect=postgresql.dialect()))

    assert "WHERE" in ddl
    assert "user_id IS NOT NULL" in ddl
    assert "status = 'active'" in ddl


def test_finalization_database_error_is_not_reported_as_hash_replay(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Distinguish an order database failure from genuine transaction replay.

    Params:
        client: Isolated agent checkout HTTP client.
        monkeypatch: Fixture simulating a non-replay database constraint failure.

    Returns:
        None. The unpaid intent remains intact and the response identifies finalization.
    """
    order = _create_order(client)

    def fail_commit(session: Session) -> None:
        """Raise a controlled non-replay constraint failure during finalization.

        Params:
            session: SQLAlchemy session attempting to commit the verified order.

        Returns:
            None. Always raises the simulated integrity error.
        """
        raise IntegrityError("UPDATE carts", {}, RuntimeError("private-database-detail"))

    monkeypatch.setattr(Session, "commit", fail_commit)
    response = client.post(
        f"/agent/payment-intents/{order['payment_intent_id']}/confirm",
        headers=AGENT_HEADERS,
        json={"tx_hash": "0xgood"},
    )

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "ORDER_FINALIZATION_FAILED"
    assert "private-database-detail" not in response.text
    with SessionLocal() as db:
        intent = db.get(PaymentIntent, order["payment_intent_id"])
        assert intent.status == "requires_payment"
        assert intent.tx_hash is None


def test_demo_user_can_keep_active_cart_and_multiple_paid_orders(client: TestClient) -> None:
    """Allow two paid agent orders while the demo user's normal cart remains active.

    Params:
        client: Isolated checkout HTTP client with a deterministic receipt verifier.

    Returns:
        None. One active cart and multiple paid orders coexist for the demo user.
    """
    with SessionLocal() as db:
        user = User(email="agent-demo@example.com", password_hash="unused-test-hash")
        db.add(user)
        db.flush()
        db.add(Cart(user_id=user.id, status="active"))
        db.commit()

    for tx_hash in ("0xgood", "0xsecondgood"):
        order = _create_order(client)
        response = client.post(
            f"/agent/payment-intents/{order['payment_intent_id']}/confirm",
            headers=AGENT_HEADERS,
            json={"tx_hash": tx_hash},
        )
        assert response.status_code == 200

    with SessionLocal() as db:
        user = db.query(User).filter(User.email == "agent-demo@example.com").one()
        assert db.query(Cart).filter(Cart.user_id == user.id, Cart.status == "active").count() == 1
        assert db.query(Cart).filter(Cart.user_id == user.id, Cart.status == "ordered").count() == 2


def test_receipt_verifier_requires_successful_exact_usdc_transfer() -> None:
    """
    Verify receipt parsing accepts only successful exact USDC merchant transfers.

    Params:
        None.

    Returns:
        None. Assertions cover successful, failed, wrong-recipient, and wrong-amount receipts.
    """
    expected = amount_cents_to_usdc_base_units(1100)
    assert receipt_has_exact_usdc_transfer(
        _transfer_receipt(value=expected),
        usdc_contract_address=USDC,
        pay_to=MERCHANT,
        amount_base_units=expected,
    ).verified
    assert receipt_has_exact_usdc_transfer(
        _transfer_receipt(status=0, value=expected),
        usdc_contract_address=USDC,
        pay_to=MERCHANT,
        amount_base_units=expected,
    ).reason_code == "RECEIPT_FAILED"
    assert receipt_has_exact_usdc_transfer(
        _transfer_receipt(to="0x2222222222222222222222222222222222222222", value=expected),
        usdc_contract_address=USDC,
        pay_to=MERCHANT,
        amount_base_units=expected,
    ).reason_code == "WRONG_RECIPIENT"
    assert receipt_has_exact_usdc_transfer(
        _transfer_receipt(value=expected - 1),
        usdc_contract_address=USDC,
        pay_to=MERCHANT,
        amount_base_units=expected,
    ).reason_code == "WRONG_AMOUNT"
