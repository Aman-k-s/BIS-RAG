from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def run_step(command: list[str]) -> None:
    completed = subprocess.run(command, check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def main() -> None:
    root = Path(__file__).resolve().parent
    pdf_path = root / "data" / "dataset.pdf"
    db_path = root / "data" / "standards_db.json"
    required_artifacts = [
        root / "data" / "standards_db.json",
        root / "data" / "faiss_index.bin",
        root / "data" / "bm25_index.pkl",
        root / "data" / "index_ids.json",
        root / "data" / "index_metadata.json",
    ]

    if not pdf_path.exists():
        raise SystemExit(f"Dataset PDF not found: {pdf_path}")

    if all(path.exists() for path in required_artifacts):
        print("Artifacts already exist. Skipping rebuild.")
        return

    run_step([sys.executable, str(root / "src" / "ingest.py"), "--pdf", str(pdf_path), "--output", str(db_path)])
    run_step([sys.executable, str(root / "src" / "indexer.py"), "--db", str(db_path), "--output_dir", str(root / "data")])


if __name__ == "__main__":
    main()
