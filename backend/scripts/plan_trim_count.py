from __future__ import annotations

import csv
import random
from collections import Counter, defaultdict
from pathlib import Path

ARTICLES_CSV = Path("data/articles.csv")
IMAGES_INDEX_CSV = Path("data/index/images_index.csv")

OUT_DIR = Path("data/trimmed_plan")
OUT_DIR.mkdir(parents=True, exist_ok=True)

SELECTED_IDS = OUT_DIR / "selected_article_ids.txt"
SELECTED_MEMBERS = OUT_DIR / "selected_members.txt"
TRIMMED_CATALOG = OUT_DIR / "catalog_trimmed.csv"
PLAN_REPORT = OUT_DIR / "plan_report.txt"

# ====== TUNE THESE ======
TARGET_N = 4000
SEED = 42

# quota mix (broad Ladies + Mens, include Sport)
QUOTA_WEIGHTS = {
    "Ladieswear": 0.40,
    "Menswear": 0.40,
    "Sport": 0.10,
    "Divided": 0.10,
}
# =======================


def load_images_index():
    # article_id -> (member, size)
    idx = {}
    with IMAGES_INDEX_CSV.open("r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            aid = row["article_id"].strip().zfill(10)
            idx[aid] = (row["member"], int(row["uncompressed_bytes"]))
    return idx


def load_articles():
    with ARTICLES_CSV.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_trimmed_catalog(rows, selected_ids_set, out_csv):
    filtered = [
        r for r in rows
        if str(r.get("article_id", "")).strip().zfill(10) in selected_ids_set
    ]
    if not filtered:
        raise RuntimeError("No rows selected. Check that articles.csv matches the image index.")

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(filtered[0].keys()))
        w.writeheader()
        w.writerows(filtered)


def sample_within_group_stratified(rows, img_idx, n, seed):
    """
    Random sample within a single index_group_name, but diversify via product_group_name buckets.
    Round-robin across product groups until n reached.
    """
    rng = random.Random(seed)
    buckets = defaultdict(list)

    for row in rows:
        aid = str(row.get("article_id", "")).strip().zfill(10)
        member, sz = img_idx[aid]
        pg = (row.get("product_group_name") or "Unknown").strip() or "Unknown"
        buckets[pg].append((aid, member, sz))

    groups = list(buckets.keys())
    rng.shuffle(groups)
    for g in groups:
        rng.shuffle(buckets[g])

    selected = []
    while len(selected) < n:
        progressed = False
        for g in groups:
            if not buckets[g]:
                continue
            selected.append(buckets[g].pop())
            progressed = True
            if len(selected) >= n:
                break
        if not progressed:
            break

    return selected


def main():
    img_idx = load_images_index()
    rows = load_articles()

    allowed_groups = set(QUOTA_WEIGHTS.keys())

    # Only rows that have images and are in allowed index groups
    candidates = []
    for row in rows:
        aid = str(row.get("article_id", "")).strip().zfill(10)
        if aid not in img_idx:
            continue
        ig = (row.get("index_group_name") or "").strip()
        if ig not in allowed_groups:
            continue
        candidates.append(row)

    if not candidates:
        raise RuntimeError("No candidates found. Check index_group_name values and file paths.")

    # Build integer quotas that sum to TARGET_N
    quotas = {}
    running = 0
    keys = list(QUOTA_WEIGHTS.keys())
    for k in keys[:-1]:
        q = int(TARGET_N * QUOTA_WEIGHTS[k])
        quotas[k] = q
        running += q
    quotas[keys[-1]] = TARGET_N - running  # remainder to last bucket

    rng = random.Random(SEED)
    rng.shuffle(candidates)  # break any CSV ordering

    # Group rows by index_group_name
    by_ig = defaultdict(list)
    for row in candidates:
        ig = (row.get("index_group_name") or "").strip()
        by_ig[ig].append(row)

    # Sample per group quota
    selected = []
    selected_ids_set = set()

    shortfall = 0
    achieved_counts = Counter()

    for ig, q in quotas.items():
        group_rows = by_ig.get(ig, [])
        rng.shuffle(group_rows)

        chunk = sample_within_group_stratified(group_rows, img_idx, q, SEED + (hash(ig) % 10000))
        for aid, member, sz in chunk:
            if aid in selected_ids_set:
                continue
            selected.append((aid, member, sz))
            selected_ids_set.add(aid)

        achieved_counts[ig] = len(chunk)
        if len(chunk) < q:
            shortfall += (q - len(chunk))

    # If any group couldn't fill its quota, fill remainder from remaining allowed candidates
    if len(selected) < TARGET_N:
        remaining = []
        for row in candidates:
            aid = str(row.get("article_id", "")).strip().zfill(10)
            if aid in selected_ids_set:
                continue
            member, sz = img_idx[aid]
            remaining.append((aid, member, sz))

        rng.shuffle(remaining)
        for aid, member, sz in remaining:
            if len(selected) >= TARGET_N:
                break
            selected.append((aid, member, sz))
            selected_ids_set.add(aid)

    # Final shuffle so output isn't grouped by category
    rng.shuffle(selected)

    selected_ids = [aid for aid, _, _ in selected]
    selected_members = [m for _, m, _ in selected]
    total_bytes = sum(sz for _, _, sz in selected)

    # Keep randomness: do NOT sort
    SELECTED_IDS.write_text("\n".join(selected_ids))
    SELECTED_MEMBERS.write_text("\n".join(selected_members))

    write_trimmed_catalog(rows, set(selected_ids), TRIMMED_CATALOG)

    summary = (
        f"Target N: {TARGET_N}\n"
        f"Seed: {SEED}\n"
        f"Quota weights: {QUOTA_WEIGHTS}\n"
        f"Quotas used: {quotas}\n"
        f"Achieved counts: {dict(achieved_counts)}\n"
        f"Estimated extracted size (GB): {total_bytes/1024**3:.3f}\n"
        f"Outputs:\n"
        f" - {SELECTED_IDS}\n"
        f" - {SELECTED_MEMBERS}\n"
        f" - {TRIMMED_CATALOG}\n"
    )
    PLAN_REPORT.write_text(summary)
    print(summary)


if __name__ == "__main__":
    main()
