from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from src.pipeline import BISPipeline


def ensure_artifacts(root: Path) -> None:
    required = [
        root / "data" / "standards_db.json",
        root / "data" / "faiss_index.bin",
        root / "data" / "bm25_index.pkl",
        root / "data" / "index_ids.json",
        root / "data" / "index_metadata.json",
    ]
    if all(path.exists() for path in required):
        return
    subprocess.run([sys.executable, str(root / "setup.py")], check=True)


def normalize_std(std_string: str) -> str:
    return str(std_string).replace(" ", "").lower()


def evaluate_results(results: list[dict[str, Any]]) -> dict[str, float] | None:
    if not results:
        return None
    if not all(item.get("expected_standards") for item in results):
        return None

    hits_at_3 = 0
    mrr_sum_at_5 = 0.0
    total_latency = 0.0

    for item in results:
        expected = set(normalize_std(std) for std in item.get("expected_standards", []))
        retrieved = [normalize_std(std) for std in item.get("retrieved_standards", [])]
        total_latency += float(item.get("latency_seconds", 0.0))

        if any(std in expected for std in retrieved[:3]):
            hits_at_3 += 1

        reciprocal_rank = 0.0
        for rank, std in enumerate(retrieved[:5], start=1):
            if std in expected:
                reciprocal_rank = 1.0 / rank
                break
        mrr_sum_at_5 += reciprocal_rank

    total_queries = len(results)
    return {
        "hit_rate_at_3": round((hits_at_3 / total_queries) * 100, 2),
        "mrr_at_5": round(mrr_sum_at_5 / total_queries, 4),
        "avg_latency_seconds": round(total_latency / total_queries, 4),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run BIS recommendations on an input JSON file.")
    parser.add_argument("--input", required=True, help="Path to input JSON.")
    parser.add_argument("--output", required=True, help="Path to output JSON.")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    ensure_artifacts(root)

    input_path = Path(args.input)
    output_path = Path(args.output)

    payload = json.loads(input_path.read_text(encoding="utf-8"))
    items = payload if isinstance(payload, list) else [payload]
    pipeline = BISPipeline(root / "data")

    results = []
    for item in items:
        result = pipeline.run(item["query"])
        results.append(
            {
                "id": item["id"],
                "query": item["query"],
                "expected_standards": item.get("expected_standards", []),
                "retrieved_standards": result["retrieved_standards"],
                "rationale": result["rationale"],
                "llm": result["llm"],
                "timing_breakdown_seconds": result["timing_breakdown_seconds"],
                "latency_seconds": result["latency_seconds"],
            }
        )

    output_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

    metrics = evaluate_results(results)
    if metrics is None:
        print("Inference completed.")
        print("Metrics not computed because expected_standards were not provided for every item.")
    else:
        print("Inference completed.")
        print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
