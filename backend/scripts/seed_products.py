from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session
from sqlalchemy.dialects.sqlite import insert

from app.core.db import SessionLocal
from app.db.models import Product

from sqlalchemy import text


CSV_PATH = Path("data/catalog_trimmed_priced.csv")


def to_int(v: Any) -> int | None:
    if v in (None, ""):
        return None
    try:
        return int(v)
    except ValueError:
        try:
            return int(float(v))
        except ValueError:
            return None


def to_str(v: Any) -> str | None:
    if v in (None, ""):
        return None
    return str(v)


def main():
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"CSV not found: {CSV_PATH.resolve()}")

    db: Session = SessionLocal()
    try:
        # Helps if SQLite is busy during bulk inserts
        db.connection().exec_driver_sql("PRAGMA busy_timeout = 5000;")

        MAX_SQL_VARS = 900  # safe under typical 999 default

        batch: list[dict[str, Any]] = []
        BATCH_SIZE: int | None = None
        inserted = 0

        with CSV_PATH.open("r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                article_id = row.get("article_id")
                prod_name = row.get("prod_name")
                if not article_id or not prod_name:
                    continue

                price_cents = to_int(row.get("price_cents"))
                price = (price_cents / 100.0) if price_cents is not None else None

                row_dict: dict[str, Any] = {
                    # PK
                    "id": str(article_id),

                    # convenience fields
                    "name": str(prod_name),
                    "category": to_str(row.get("product_group_name")),
                    "price": price,
                    "description": to_str(row.get("detail_desc")),
                    "color": to_str(row.get("colour_group_name")),

                    "image_key": None,
                    "has_image": False,

                    # full CSV fields
                    "product_code": to_int(row.get("product_code")),
                    "prod_name": to_str(row.get("prod_name")),
                    "product_type_no": to_int(row.get("product_type_no")),
                    "product_type_name": to_str(row.get("product_type_name")),
                    "product_group_name": to_str(row.get("product_group_name")),
                    "graphical_appearance_no": to_int(row.get("graphical_appearance_no")),
                    "graphical_appearance_name": to_str(row.get("graphical_appearance_name")),
                    "colour_group_code": to_int(row.get("colour_group_code")),
                    "colour_group_name": to_str(row.get("colour_group_name")),
                    "perceived_colour_value_id": to_int(row.get("perceived_colour_value_id")),
                    "perceived_colour_value_name": to_str(row.get("perceived_colour_value_name")),
                    "perceived_colour_master_id": to_int(row.get("perceived_colour_master_id")),
                    "perceived_colour_master_name": to_str(row.get("perceived_colour_master_name")),
                    "department_no": to_int(row.get("department_no")),
                    "department_name": to_str(row.get("department_name")),
                    "index_code": to_str(row.get("index_code")),
                    "index_name": to_str(row.get("index_name")),
                    "index_group_no": to_int(row.get("index_group_no")),
                    "index_group_name": to_str(row.get("index_group_name")),
                    "section_no": to_int(row.get("section_no")),
                    "section_name": to_str(row.get("section_name")),
                    "garment_group_no": to_int(row.get("garment_group_no")),
                    "garment_group_name": to_str(row.get("garment_group_name")),
                    "detail_desc": to_str(row.get("detail_desc")),
                    "price_cents": price_cents,
                    "currency": to_str(row.get("currency")),
                }

                if BATCH_SIZE is None:
                    cols = len(row_dict.keys())
                    BATCH_SIZE = max(1, min(200, MAX_SQL_VARS // cols))
                    print(f"Using BATCH_SIZE={BATCH_SIZE} for {cols} columns (SQLite var limit safe).")

                batch.append(row_dict)

                if len(batch) >= BATCH_SIZE:
                    inserted += upsert_batch(db, batch)
                    batch.clear()

            if batch:
                inserted += upsert_batch(db, batch)

        print(f"Upserted {inserted} products into SQLite.")
    finally:
        db.close()


def upsert_batch(db: Session, rows: list[dict[str, Any]]) -> int:
    stmt = insert(Product).values(rows)
    # Update all provided fields on conflict (except PK)
    stmt = stmt.on_conflict_do_update(
        index_elements=[Product.id],
        set_={k: getattr(stmt.excluded, k) for k in rows[0].keys() if k != "id"},
    )
    result = db.execute(stmt)
    db.commit()
    return result.rowcount or 0


if __name__ == "__main__":
    main()
