from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from rapidfuzz import process, fuzz

# Lazy-loaded globals
_MODEL: SentenceTransformer | None = None
_INDEX: faiss.Index | None = None
_IDMAP: list[str] | None = None
_VOCAB: dict[str, list[str]] | None = None

def _paths() -> tuple[Path, Path, Path]:
    here = Path(__file__).resolve()
    backend_root = here.parents[1]  # backend/
    project_root = backend_root if (backend_root / "data").exists() else backend_root.parent
    out_dir = project_root / "data" / "semantic"
    return (
        out_dir / "faiss.index",
        out_dir / "id_map.json",
        out_dir / "vocab.json",
    )

def load_search_assets(model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
    global _MODEL, _INDEX, _IDMAP, _VOCAB
    if _MODEL is not None and _INDEX is not None and _IDMAP is not None:
        return

    index_path, idmap_path, vocab_path = _paths()
    if not index_path.exists() or not idmap_path.exists():
        raise RuntimeError(
            f"Semantic index not found. Run build script first.\nMissing: {index_path} or {idmap_path}"
        )

    _MODEL = SentenceTransformer(model_name, backend="onnx")
    _INDEX = faiss.read_index(str(index_path))
    _IDMAP = json.loads(idmap_path.read_text(encoding="utf-8"))

    if vocab_path.exists():
        _VOCAB = json.loads(vocab_path.read_text(encoding="utf-8"))
    else:
        _VOCAB = {}

def _best_fuzzy_match(query: str, choices: list[str], score_cutoff: int = 85) -> Optional[str]:
    if not query or not choices:
        return None
    match = process.extractOne(
        query,
        choices,
        scorer=fuzz.WRatio,
        score_cutoff=score_cutoff,
    )
    return match[0] if match else None

def parse_query_intent(q: str) -> dict[str, Optional[str]]:
    """
    Light NLP: try to detect a color master or group mentioned in the query.
    We do fuzzy matching against the known vocab lists.
    """
    qn = (q or "").strip()
    if not qn:
        return {"group": None, "color": None, "color_master": None}

    vocab = _VOCAB or {}
    group = _best_fuzzy_match(qn, vocab.get("product_group_name", []), score_cutoff=88)
    color = _best_fuzzy_match(qn, vocab.get("colour_group_name", []), score_cutoff=88)
    color_master = _best_fuzzy_match(qn, vocab.get("perceived_colour_master_name", []), score_cutoff=88)

    return {"group": group, "color": color, "color_master": color_master}

def semantic_search_ids(
    q: str,
    top_k: int = 200,
) -> list[tuple[str, float]]:
    """
    Returns list of (product_id, score) from FAISS nearest neighbors.
    """
    load_search_assets()
    assert _MODEL is not None and _INDEX is not None and _IDMAP is not None

    query = (q or "").strip()
    if not query:
        return []

    vec = _MODEL.encode([query], normalize_embeddings=True).astype("float32")
    scores, idxs = _INDEX.search(vec, top_k)

    out: list[tuple[str, float]] = []
    for score, ix in zip(scores[0].tolist(), idxs[0].tolist()):
        if ix < 0:
            continue
        pid = _IDMAP[ix]
        out.append((pid, float(score)))
    return out

def apply_fuzzy_boosts(
    results: list[dict],
    intent: dict[str, Optional[str]],
) -> list[dict]:
    """
    Simple rerank boost:
      - if intent color_master matches product's perceived colour master -> boost
      - if intent group matches product_group_name -> boost
    """
    group = (intent.get("group") or "").strip().lower()
    color_master = (intent.get("color_master") or "").strip().lower()
    color = (intent.get("color") or "").strip().lower()

    def score_item(p: dict) -> float:
        s = float(p.get("_score", 0.0))
        pg = str(p.get("product_group_name", "")).strip().lower()
        cm = str(p.get("perceived_colour_master_name", "")).strip().lower()
        cg = str(p.get("colour_group_name", "")).strip().lower()

        if group and pg == group:
            s += 0.15
        if color_master and cm == color_master:
            s += 0.12
        if color and cg == color:
            s += 0.08
        return s

    results.sort(key=score_item, reverse=True)
    return results
