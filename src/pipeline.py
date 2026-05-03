from __future__ import annotations

import time
from pathlib import Path
from typing import Dict

from .disambiguator import apply_disambiguation
from .generator import RationaleGenerator
from .reranker import rerank
from .retriever import HybridRetriever


class BISPipeline:
    def __init__(self, data_dir: str | Path = "data") -> None:
        self.data_dir = Path(data_dir)
        self.retriever = HybridRetriever(self.data_dir)
        self.generator = RationaleGenerator()

    def run(self, query: str) -> Dict[str, object]:
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

        retrieved = [candidate["record"]["full_id"] for candidate in top_candidates]

        rationale_start = time.perf_counter()
        rationale = self.generator.generate(query, top_candidates)
        rationale_time = time.perf_counter() - rationale_start

        latency = time.perf_counter() - start

        return {
            "retrieved_standards": retrieved,
            "top_candidates": [
                {
                    "full_id": candidate["record"]["full_id"],
                    "title": candidate["record"]["title"],
                    "scope": candidate["record"]["scope"],
                    "score": round(float(candidate["score"]), 4),
                }
                for candidate in top_candidates
            ],
            "llm": self.generator.info(),
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
