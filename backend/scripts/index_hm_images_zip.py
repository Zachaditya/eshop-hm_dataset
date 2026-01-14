from __future__ import annotations

import csv
import json
import zipfile
from pathlib import Path

ZIP_PATH = Path("data/images.zip")
OUT_DIR = Path("data/index")
OUT_DIR.mkdir(parents=True, exist_ok=True)

INDEX_CSV = OUT_DIR / "images_index.csv"
REPORT_JSON = OUT_DIR / "report.json"
IDS_TXT = OUT_DIR / "article_ids_with_images.txt"

def main():
    if not ZIP_PATH.exists():
        raise FileNotFoundError(ZIP_PATH)

    total_uncompressed = 0
    count = 0
    ids = set()

    with zipfile.ZipFile(ZIP_PATH) as z, INDEX_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["article_id", "member", "uncompressed_bytes"])

        for info in z.infolist():
            name = info.filename
            if not name.lower().endswith(".jpg"):
                continue

            stem = Path(name).stem
            # entries are like 010/0108775015.jpg -> stem is 0108775015
            if not stem.isdigit():
                continue

            aid = stem.zfill(10)
            ids.add(aid)

            w.writerow([aid, name, info.file_size])

            count += 1
            total_uncompressed += info.file_size

    report = {
        "zip": str(ZIP_PATH),
        "image_files": count,
        "unique_article_ids_with_images": len(ids),
        "total_uncompressed_gb": round(total_uncompressed / (1024**3), 3),
        "avg_uncompressed_kb": round((total_uncompressed / max(count, 1)) / 1024, 2),
        "index_csv": str(INDEX_CSV),
    }

    REPORT_JSON.write_text(json.dumps(report, indent=2))
    IDS_TXT.write_text("\n".join(sorted(ids)))

    print(json.dumps(report, indent=2))
    print(f"\nWrote:\n- {INDEX_CSV}\n- {REPORT_JSON}\n- {IDS_TXT}")

if __name__ == "__main__":
    main()
