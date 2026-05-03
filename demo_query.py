from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.pipeline import BISPipeline
from inference import evaluate_results


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one interactive/demo query through the BIS RAG pipeline.")
    parser.add_argument("--query", help="Natural-language product/compliance query.")
    parser.add_argument("--expected", help="Optional comma-separated expected standard IDs for scoring.")
    parser.add_argument("--data-dir", default="data", help="Directory containing built RAG artifacts.")
    parser.add_argument("--json", action="store_true", help="Print the full result as JSON.")
    parser.add_argument("--require-llm", action="store_true", help="Fail if the LLM is not actually used.")
    args = parser.parse_args()

    query = args.query or input("Enter your query: ").strip()
    if not query:
        raise SystemExit("Query is required.")

    expected_raw = args.expected
    if expected_raw is None:
        expected_raw = input("Expected standard(s) for metrics, comma-separated (optional): ").strip()
    expected_standards = [item.strip() for item in expected_raw.split(",") if item.strip()] if expected_raw else []

    pipeline = BISPipeline(Path(args.data_dir))
    result = pipeline.run(query)

    if args.require_llm and result["llm"]["last_generation_mode"] != "llm":
        raise SystemExit(
            f"LLM was required, but generation mode was '{result['llm']['last_generation_mode']}' "
            f"with status '{result['llm']['status']}'."
        )

    output = {
        "id": "interactive-query",
        "query": query,
        "expected_standards": expected_standards,
        "retrieved_standards": result["retrieved_standards"],
        "match_decision": result["match_decision"],
        "top_candidates": result["top_candidates"],
        "rationale": result["rationale"],
        "llm": result["llm"],
        "timing_breakdown_seconds": result["timing_breakdown_seconds"],
        "latency_seconds": result["latency_seconds"],
    }
    metrics = evaluate_results([output]) if expected_standards else None

    if args.json:
        payload = {"result": output, "metrics": metrics}
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    print("LLM:")
    print(f"  enabled: {result['llm']['llm_enabled']}")
    print(f"  provider: {result['llm']['provider']}")
    print(f"  model: {result['llm']['model_name']}")
    print(f"  status: {result['llm']['status']}")
    print(f"  generation_mode: {result['llm']['last_generation_mode']}")
    print()
    print(f"Match decision: {result['match_decision']}")
    print()
    print("Top standards:")
    for index, candidate in enumerate(result["top_candidates"], start=1):
        print(f"  {index}. {candidate['full_id']} | score={candidate['score']}")
        print(f"     {candidate['title']}")
    print()
    print("Rationale:")
    print(result["rationale"])
    print()
    print("Latency breakdown:")
    for key, value in result["timing_breakdown_seconds"].items():
        print(f"  {key}: {value} sec")
    if metrics:
        print()
        print("Metrics:")
        for key, value in metrics.items():
            print(f"  {key}: {value}")
    else:
        print()
        print("Metrics: not computed because no expected standard was provided.")


if __name__ == "__main__":
    main()
