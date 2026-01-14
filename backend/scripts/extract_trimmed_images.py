from __future__ import annotations

import zipfile
from pathlib import Path

ZIP_PATH = Path("data/images.zip")
MEMBERS_TXT = Path("data/trimmed_plan/selected_members.txt")
OUT_DIR = Path("data/images")


def folder_size_bytes(path: Path) -> int:
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())


def main():
    members = [line.strip() for line in MEMBERS_TXT.read_text().splitlines() if line.strip()]
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(ZIP_PATH) as z:
        for i, m in enumerate(members, 1):
            z.extract(m, path=OUT_DIR)
            if i % 500 == 0:
                print(f"Extracted {i}/{len(members)}")

    size_gb = folder_size_bytes(OUT_DIR) / (1024**3)
    print(f"Done. Extracted folder: {OUT_DIR}")
    print(f"Actual extracted size: {size_gb:.3f} GB")


if __name__ == "__main__":
    main()
