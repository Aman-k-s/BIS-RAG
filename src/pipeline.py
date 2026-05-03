from __future__ import annotations

import time
from pathlib import Path
from typing import Dict

from .disambiguator import apply_disambiguation
from .generator import RationaleGenerator
from .reranker import rerank
from .retriever import HybridRetriever


class BISPipeline:
    MIN_CONFIDENCE_SCORE = 0.7

    def __init__(self, data_dir: str | Path = "data") -> None:
        self.data_dir = Path(data_dir)
        self.retriever = HybridRetriever(self.data_dir)
        self.generator = RationaleGenerator()

    def is_confident_match(self, top_candidates: list[dict[str, object]]) -> bool:
        if not top_candidates:
            return False
        top_score = float(top_candidates[0]["score"])
        return top_score >= self.MIN_CONFIDENCE_SCORE

    def run(self, query: str, generate_rationale: bool = True) -> Dict[str, object]:
        start = time.perf_counter()

        retrieval_start = time.perf_counter()
        candidates = self.retriever.retrieve(query, top_k=20)
        retrieval_time = time.perf_counter() - retrieval_start

        disambiguation_start = time.perf_counter()
        candidates = apply_disambiguation(query, candidates)
        disambiguation_time = time.perf_counter() - disambiguation_start

        rerank_start = time.perf_counter()
        top_candidates = rerank(query, candidates, top_k=5)
        rerank_time = time.perf_counter() - rerank_start

        confident_match = self.is_confident_match(top_candidates)
        retrieved = [candidate["record"]["full_id"] for candidate in top_candidates] if confident_match else []

        rationale_start = time.perf_counter()
        if generate_rationale:
            if confident_match:
                rationale = self.generator.generate(query, top_candidates)
            else:
                rationale = (
                    "I could not confidently identify a matching BIS standard from the indexed building materials domain "
                    "for this query. Please refine the query or verify whether it belongs to the current BIS dataset scope."
                )
            rationale_time = time.perf_counter() - rationale_start
            llm_info = self.generator.info()
        else:
            rationale = ""
            rationale_time = 0.0
            llm_info = {
                "provider": "disabled",
                "model_name": "not-used-in-batch-inference",
                "llm_enabled": "false",
                "status": "disabled-for-inference",
                "last_generation_mode": "disabled",
                "last_error": "",
            }

        latency = time.perf_counter() - start

        return {
            "retrieved_standards": retrieved,
            "match_decision": "confident-match" if confident_match else "no-confident-match",
            "top_candidates": [
                {
                    "full_id": candidate["record"]["full_id"],
                    "title": candidate["record"]["title"],
                    "scope": candidate["record"]["scope"],
                    "score": round(float(candidate["score"]), 4),
                }
                for candidate in top_candidates
            ],
            "llm": llm_info,
            "rationale": rationale,
            "timing_breakdown_seconds": {
                "retrieval": round(retrieval_time, 4),
                "disambiguation": round(disambiguation_time, 4),
                "reranking": round(rerank_time, 4),
                "rationale_generation": round(rationale_time, 4),
                "total": round(latency, 4),
            },
            "latency_seconds": round(latency, 4),
        }
