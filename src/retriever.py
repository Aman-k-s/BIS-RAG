from __future__ import annotations

import json
import os
import pickle
from pathlib import Path
from typing import Dict, List

import faiss
import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

from .synonyms import expand_query


_QUERY_CACHE_MAX = 256


def tokenize(text: str) -> List[str]:
    return text.lower().split()


def reciprocal_rank_fusion(rankings: List[List[str]]) -> Dict[str, float]:
    scores: Dict[str, float] = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (60 + rank)
    return scores


def _configure_torch_threads() -> None:
    if os.environ.get("BIS_SKIP_TORCH_THREAD_CONFIG"):
        return
    try:
        import torch  # noqa: WPS433 (deliberate local import)

        target = max(1, (os.cpu_count() or 1))
        torch.set_num_threads(target)
    except Exception:
        pass


class HybridRetriever:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.records = json.loads((data_dir / "standards_db.json").read_text(encoding="utf-8"))
        for record in self.records:
            title = str(record.get("title", ""))
            scope = str(record.get("scope", ""))
            record["_lower_text"] = f"{title} {scope}".lower()
        self.record_map = {record["full_id"]: record for record in self.records}
        self.index_ids = json.loads((data_dir / "index_ids.json").read_text(encoding="utf-8"))
        self.id_to_index = {doc_id: idx for idx, doc_id in enumerate(self.index_ids)}
        self.index_metadata = json.loads((data_dir / "index_metadata.json").read_text(encoding="utf-8"))
        self.faiss_index = faiss.read_index(str(data_dir / "faiss_index.bin"))

        with (data_dir / "bm25_index.pkl").open("rb") as handle:
            self.bm25: BM25Okapi = pickle.load(handle)

        _configure_torch_threads()

        model_name = self.index_metadata["embedding_model"]
        self.embedding_model = SentenceTransformer(model_name, local_files_only=True)
        self._query_cache: Dict[str, np.ndarray] = {}

    def _encode_query(self, expanded_query: str) -> np.ndarray:
        cached = self._query_cache.get(expanded_query)
        if cached is not None:
            return cached

        vector = self.embedding_model.encode(
            [expanded_query],
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        if vector.dtype != np.float32:
            vector = vector.astype(np.float32, copy=False)

        if len(self._query_cache) >= _QUERY_CACHE_MAX:
            self._query_cache.clear()
        self._query_cache[expanded_query] = vector
        return vector

    def section_boost(self, query: str, record: Dict[str, object]) -> float:
        lower_query = query.lower()
        section = record["section"]
        if any(term in lower_query for term in ["cement", "concrete", "masonry", "aggregate"]):
            if section in {"cement", "concrete", "aggregates", "masonry", "pipes"}:
                return 0.04
        return 0.0

    def retrieve(self, query: str, top_k: int = 20) -> List[Dict[str, object]]:
        expanded_query = expand_query(query)

        vector = self._encode_query(expanded_query)
        dense_scores, dense_indices = self.faiss_index.search(vector, top_k)
        dense_scores = dense_scores[0]
        dense_indices = dense_indices[0]

        sparse_scores = np.asarray(self.bm25.get_scores(tokenize(expanded_query)), dtype="float32")

        dense_ranking = [self.index_ids[idx] for idx in dense_indices if idx >= 0]

        sparse_n = sparse_scores.shape[0]
        if sparse_n == 0:
            sparse_ranking: List[str] = []
        else:
            top_n = min(top_k, sparse_n)
            if top_n >= sparse_n:
                top_idx = np.argsort(-sparse_scores)
            else:
                partitioned = np.argpartition(-sparse_scores, top_n)[:top_n]
                top_idx = partitioned[np.argsort(-sparse_scores[partitioned])]
            sparse_ranking = [self.index_ids[int(i)] for i in top_idx]

        fused = reciprocal_rank_fusion([dense_ranking, sparse_ranking])

        dense_pos: Dict[int, int] = {}
        for position, faiss_idx in enumerate(dense_indices):
            int_idx = int(faiss_idx)
            if int_idx >= 0 and int_idx not in dense_pos:
                dense_pos[int_idx] = position

        candidates: List[Dict[str, object]] = []
        for doc_id, base_score in fused.items():
            record = self.record_map[doc_id]
            idx = self.id_to_index[doc_id]
            position = dense_pos.get(idx)
            dense_bonus = float(dense_scores[position]) if position is not None else 0.0
            bonus = self.section_boost(query, record)
            combined_score = base_score + bonus + (0.03 * dense_bonus) + (0.02 * float(sparse_scores[idx]))
            candidates.append({"record": record, "score": combined_score})

        candidates.sort(key=lambda item: item["score"], reverse=True)
        return candidates[:top_k]
