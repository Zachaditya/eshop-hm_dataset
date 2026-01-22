#!/usr/bin/env python3
from __future__ import annotations

import json
import csv
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

# ---------- paths ----------
HERE = Path(__file__).resolve()
BACKEND_ROOT = HERE.parents[1]  # backend/
PROJECT_ROOT = BACKEND_ROOT if (BACKEND_ROOT / "data").exists() else BACKEND_ROOT.parent

CSV_PATH = PROJECT_ROOT / "data" / "catalog_trimmed_priced.csv"
OUT_DIR = PROJECT_ROOT / "data" / "semantic"
OUT_DIR.mkdir(parents=True, exist_ok=True)

INDEX_PATH = OUT_DIR / "faiss.index"
IDMAP_PATH = OUT_DIR / "id_map.json"
VOCAB_PATH = OUT_DIR / "vocab.json"

# ---------- config ----------
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
BATCH_SIZE = 128

FIELDS = [
    "prod_name",
    "product_group_name",
    "product_type_name",
    "department_name",
    "section_name",
    "colour_group_name",
    "perceived_colour_master_name",
    "detail_desc",
]

def build_search_text(row: dict) -> str:
    # Robustly read fields (some CSVs might omit a column)
    parts = []
    def add(label: str, key: str):
        v = (row.get(key) or "").strip()
        if v:
            parts.append(f"{label}: {v}")

    add("name", "prod_name")
    add("group", "product_group_name")
    add("type", "product_type_name")
    add("department", "department_name")
    add("section", "section_name")
    add("color", "colour_group_name")
    add("color_master", "perceived_colour_master_name")
    add("desc", "detail_desc")

    return " | ".join(parts)

def main():
    if not CSV_PATH.exists():
        raise SystemExit(f"CSV not found: {CSV_PATH}")

    # Load rows + build texts
    product_ids: List[str] = []
    texts: List[str] = []

    groups = set()
    colors = set()
    color_masters = set()
    types = set()

    with CSV_PATH.open("r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            # image system uses article_id
            pid = str(row["article_id"]).strip()
            if not pid:
                continue

            # collect vocab for fuzzy parsing
            g = (row.get("product_group_name") or "").strip()
            if g: groups.add(g)

            c = (row.get("colour_group_name") or "").strip()
            if c: colors.add(c)

            cm = (row.get("perceived_colour_master_name") or "").strip()
            if cm: color_masters.add(cm)

            t = (row.get("product_type_name") or "").strip()
            if t: types.add(t)

            product_ids.append(pid)
            texts.append(build_search_text(row))

    print(f"Loaded {len(texts)} products from {CSV_PATH}")

    # Embed
    model = SentenceTransformer(MODEL_NAME, backend = "onnx")
    emb = model.encode(
        texts,
        batch_size=BATCH_SIZE,
        normalize_embeddings=True,   # cosine similarity via dot product
        show_progress_bar=True,
    ).astype("float32")

    # Build FAISS index (inner product works as cosine because normalized)
    dim = emb.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(emb)

    faiss.write_index(index, str(INDEX_PATH))
    IDMAP_PATH.write_text(json.dumps(product_ids), encoding="utf-8")

    vocab = {
        "product_group_name": sorted(groups),
        "colour_group_name": sorted(colors),
        "perceived_colour_master_name": sorted(color_masters),
        "product_type_name": sorted(types),
        "model": MODEL_NAME,
        "count": len(product_ids),
    }
    VOCAB_PATH.write_text(json.dumps(vocab, indent=2), encoding="utf-8")

    print("Wrote:")
    print(f"  {INDEX_PATH}")
    print(f"  {IDMAP_PATH}")
    print(f"  {VOCAB_PATH}")

if __name__ == "__main__":
    main()
