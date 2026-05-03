from __future__ import annotations

import json
import pickle
from pathlib import Path
from typing import Dict, List

import faiss
import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

from .synonyms import expand_query


def tokenize(text: str) -> List[str]:
    return text.lower().split()


def reciprocal_rank_fusion(rankings: List[List[str]]) -> Dict[str, float]:
    scores: Dict[str, float] = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (60 + rank)
    return scores


class HybridRetriever:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.records = json.loads((data_dir / "standards_db.json").read_text(encoding="utf-8"))
        self.record_map = {record["full_id"]: record for record in self.records}
        self.index_ids = json.loads((data_dir / "index_ids.json").read_text(encoding="utf-8"))
        self.id_to_index = {doc_id: idx for idx, doc_id in enumerate(self.index_ids)}
        self.index_metadata = json.loads((data_dir / "index_metadata.json").read_text(encoding="utf-8"))
        self.faiss_index = faiss.read_index(str(data_dir / "faiss_index.bin"))

        with (data_dir / "bm25_index.pkl").open("rb") as handle:
            self.bm25: BM25Okapi = pickle.load(handle)

        model_name = self.index_metadata["embedding_model"]
        self.embedding_model = SentenceTransformer(model_name, local_files_only=True)

    def section_boost(self, query: str, record: Dict[str, object]) -> float:
        lower_query = query.lower()
        section = record["section"]
        if any(term in lower_query for term in ["cement", "concrete", "masonry", "aggregate"]):
            if section in {"cement", "concrete", "aggregates", "masonry", "pipes"}:
                return 0.04
        return 0.0

    def retrieve(self, query: str, top_k: int = 20) -> List[Dict[str, object]]:
        expanded_query = expand_query(query)
        query_vector = self.embedding_model.encode([expanded_query], normalize_embeddings=True, show_progress_bar=False)
        vector = np.asarray(query_vector, dtype="float32")
        dense_scores, dense_indices = self.faiss_index.search(vector, top_k)
        dense_scores = dense_scores[0]
        dense_indices = dense_indices[0]
        sparse_scores = np.asarray(self.bm25.get_scores(tokenize(expanded_query)), dtype="float32")

        dense_ranking = [self.index_ids[idx] for idx in dense_indices if idx >= 0]
        sparse_ranking = [self.index_ids[idx] for idx in np.argsort(-sparse_scores)[:top_k]]
        fused = reciprocal_rank_fusion([dense_ranking, sparse_ranking])

        candidates: List[Dict[str, object]] = []
        for doc_id, base_score in fused.items():
            record = self.record_map[doc_id]
            idx = self.id_to_index[doc_id]
            dense_bonus = 0.0
            if idx in dense_indices:
                dense_position = int(np.where(dense_indices == idx)[0][0])
                dense_bonus = float(dense_scores[dense_position])
            bonus = self.section_boost(query, record)
            combined_score = base_score + bonus + (0.03 * dense_bonus) + (0.02 * float(sparse_scores[idx]))
            candidates.append({"record": record, "score": combined_score})

        candidates.sort(key=lambda item: item["score"], reverse=True)
        return candidates[:top_k]
