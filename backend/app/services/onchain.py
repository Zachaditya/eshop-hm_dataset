"""Helpers for verifying exact Base Sepolia USDC transfer receipts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence


TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
USDC_BASE_UNITS_PER_CENT = 10_000


@dataclass(frozen=True)
class PaymentVerification:
    """Result of checking whether a chain receipt satisfies a payment intent."""

    verified: bool
    reason_code: str
    message: str


def amount_cents_to_usdc_base_units(amount_cents: int) -> int:
    """
    Convert a dollar-cent amount into USDC base units.

    Params:
        amount_cents: Product or cart amount expressed in cents.

    Returns:
        Integer USDC base units using the six-decimal USDC contract, where one
        cent equals 10,000 base units.
    """
    return int(amount_cents) * USDC_BASE_UNITS_PER_CENT


def _hex_text(value: Any) -> str:
    """
    Render a HexBytes, bytes, int, or string value as lowercase hex text.

    Params:
        value: Receipt field value returned by Web3.py or a test fixture.

    Returns:
        A lowercase hex string prefixed with 0x when the value can be rendered,
        or an empty string for absent values.
    """
    if value is None:
        return ""
    if isinstance(value, int):
        return hex(value).lower()
    if isinstance(value, bytes):
        return "0x" + value.hex().lower()
    text = str(value).strip().lower()
    return text


def _without_0x(value: str) -> str:
    """
    Remove a leading 0x prefix from a hex string.

    Params:
        value: Hex string that may include a 0x prefix.

    Returns:
        Lowercase hex text without the leading prefix.
    """
    text = value.lower().strip()
    return text[2:] if text.startswith("0x") else text


def normalize_address(value: str | None) -> str:
    """
    Normalize an EVM address for case-insensitive comparison.

    Params:
        value: Address string from settings, a receipt log, or a decoded topic.

    Returns:
        Lowercase address text, including the 0x prefix when supplied.
    """
    return (value or "").strip().lower()


def _topic_to_address(topic: Any) -> str:
    """
    Decode an indexed ERC-20 event topic into an EVM address.

    Params:
        topic: The 32-byte indexed topic containing a padded address.

    Returns:
        The last 20 bytes of the topic as a lowercase 0x-prefixed address, or
        an empty string when the topic cannot contain an address.
    """
    raw = _without_0x(_hex_text(topic))
    if len(raw) < 40:
        return ""
    return "0x" + raw[-40:]


def _int_from_receipt_value(value: Any) -> int | None:
    """
    Parse an integer field from a Web3 receipt or log.

    Params:
        value: Integer-like value from a receipt status or log data field.

    Returns:
        The parsed integer, or None when parsing fails.
    """
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, bytes):
        return int.from_bytes(value, "big")
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(text, 16) if text.lower().startswith("0x") else int(text)
    except ValueError:
        return None


def _receipt_get(receipt: Mapping[str, Any] | Any, key: str) -> Any:
    """
    Read a receipt field from either a mapping or an attribute-style object.

    Params:
        receipt: Receipt-like object returned by Web3.py or provided by tests.
        key: Field name to read.

    Returns:
        The field value when present, otherwise None.
    """
    if isinstance(receipt, Mapping):
        return receipt.get(key)
    return getattr(receipt, key, None)


def _log_get(log: Mapping[str, Any] | Any, key: str) -> Any:
    """
    Read a log field from either a mapping or an attribute-style object.

    Params:
        log: Event log-like object from a receipt.
        key: Field name to read.

    Returns:
        The field value when present, otherwise None.
    """
    if isinstance(log, Mapping):
        return log.get(key)
    return getattr(log, key, None)


def receipt_has_exact_usdc_transfer(
    receipt: Mapping[str, Any] | Any | None,
    *,
    usdc_contract_address: str,
    pay_to: str,
    amount_base_units: int,
) -> PaymentVerification:
    """
    Check a transaction receipt for the exact USDC transfer required by an intent.

    Params:
        receipt: Transaction receipt returned by the configured Base Sepolia RPC.
        usdc_contract_address: Expected USDC contract address.
        pay_to: Merchant recipient address from server configuration.
        amount_base_units: Required transfer amount in USDC base units.

    Returns:
        PaymentVerification describing whether the receipt contains a successful
        ERC-20 Transfer log to the merchant for the exact amount.
    """
    if receipt is None:
        return PaymentVerification(False, "RECEIPT_NOT_FOUND", "Transaction receipt was not found.")

    status = _int_from_receipt_value(_receipt_get(receipt, "status"))
    if status != 1:
        return PaymentVerification(False, "RECEIPT_FAILED", "Transaction receipt was not successful.")

    expected_contract = normalize_address(usdc_contract_address)
    expected_recipient = normalize_address(pay_to)
    expected_amount = int(amount_base_units)
    saw_transfer = False
    saw_recipient = False

    logs: Sequence[Any] = _receipt_get(receipt, "logs") or []
    for log in logs:
        log_address = normalize_address(_log_get(log, "address"))
        if log_address != expected_contract:
            continue

        topics = list(_log_get(log, "topics") or [])
        if len(topics) < 3 or _hex_text(topics[0]) != TRANSFER_TOPIC:
            continue

        saw_transfer = True
        recipient = normalize_address(_topic_to_address(topics[2]))
        if recipient != expected_recipient:
            continue

        saw_recipient = True
        value = _int_from_receipt_value(_log_get(log, "data"))
        if value == expected_amount:
            return PaymentVerification(True, "VERIFIED", "Exact USDC transfer verified.")

    if saw_recipient:
        return PaymentVerification(False, "WRONG_AMOUNT", "USDC transfer amount did not match the order total.")
    if saw_transfer:
        return PaymentVerification(False, "WRONG_RECIPIENT", "USDC transfer recipient did not match the merchant.")
    return PaymentVerification(False, "USDC_TRANSFER_NOT_FOUND", "No matching USDC Transfer log was found.")


def verify_usdc_transfer(
    tx_hash: str,
    *,
    rpc_url: str,
    usdc_contract_address: str,
    pay_to: str,
    amount_base_units: int,
) -> PaymentVerification:
    """
    Fetch and verify a Base Sepolia transaction receipt for a payment intent.

    Params:
        tx_hash: Transaction hash supplied by the agent checkout caller.
        rpc_url: Base Sepolia RPC URL used to read the transaction receipt.
        usdc_contract_address: Expected USDC contract address.
        pay_to: Merchant recipient address from server configuration.
        amount_base_units: Required transfer amount in USDC base units.

    Returns:
        PaymentVerification describing whether the chain receipt proves payment.
    """
    try:
        from web3 import Web3
    except ImportError:
        return PaymentVerification(False, "WEB3_UNAVAILABLE", "web3 is not installed.")

    try:
        web3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 10}))
        receipt = web3.eth.get_transaction_receipt(tx_hash)
    except Exception as exc:
        return PaymentVerification(False, "RECEIPT_NOT_FOUND", f"Transaction receipt could not be loaded: {exc}")

    return receipt_has_exact_usdc_transfer(
        receipt,
        usdc_contract_address=usdc_contract_address,
        pay_to=pay_to,
        amount_base_units=amount_base_units,
    )
