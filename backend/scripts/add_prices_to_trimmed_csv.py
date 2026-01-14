from __future__ import annotations

import csv
from pathlib import Path
import random

IN_CSV = Path("data/trimmed_plan/catalog_trimmed.csv")
OUT_CSV = Path("data/trimmed_plan/catalog_trimmed_priced.csv")

# Product-group price ranges in cents (USD)
RANGES = {
    "Garment Upper body": (999, 4999),
    "Garment Lower body": (1499, 6999),
    "Garment Full body": (1999, 8999),
    "Outerwear": (3999, 17999),
    "Shoes": (2999, 15999),
    "Accessories": (499, 5999),
    "Underwear/nightwear": (699, 3999),
    "Swimwear": (999, 4999),
    "Sport": (1299, 11999),
}

DEFAULT_RANGE = (999, 5999)

# Price endings to feel “retail”
ENDINGS = [99, 49, 0]  # cents endings


def choose_price_cents(article_id: str, product_group: str) -> int:
    lo, hi = RANGES.get(product_group, DEFAULT_RANGE)

    # Deterministic RNG per article_id
    rng = random.Random(int(article_id))

    base = rng.randint(lo, hi)

    # Snap to a nicer retail ending
    dollars = base // 100
    ending = rng.choice(ENDINGS)
    snapped = dollars * 100 + ending

    # keep within bounds
    return max(lo, min(hi, snapped))


def main():
    with IN_CSV.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        raise RuntimeError("Input CSV has no rows")

    # Add columns if missing
    fieldnames = list(rows[0].keys())
    if "price_cents" not in fieldnames:
        fieldnames.append("price_cents")
    if "currency" not in fieldnames:
        fieldnames.append("currency")

    for row in rows:
        aid = str(row["article_id"]).strip().zfill(10)
        pg = (row.get("product_group_name") or "").strip()
        row["price_cents"] = str(choose_price_cents(aid, pg))
        row["currency"] = "USD"

    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote priced CSV: {OUT_CSV} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
