from __future__ import annotations

import argparse
import json
import pickle
from pathlib import Path
from typing import List

import faiss
import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def tokenize(text: str) -> List[str]:
    return text.lower().split()


def load_embedding_model() -> SentenceTransformer:
    try:
        return SentenceTransformer(MODEL_NAME, local_files_only=True)
    except Exception:
        return SentenceTransformer(MODEL_NAME)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build retriever artifacts from standards JSON.")
    parser.add_argument("--db", required=True, help="Path to standards_db.json")
    parser.add_argument("--output_dir", required=True, help="Directory for index artifacts")
    args = parser.parse_args()

    db_path = Path(args.db)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    records = json.loads(db_path.read_text(encoding="utf-8"))
    texts = [record["embedding_text"] for record in records]
    ids = [record["full_id"] for record in records]

    corpus_tokens = [tokenize(text) for text in texts]
    bm25 = BM25Okapi(corpus_tokens)
    with (output_dir / "bm25_index.pkl").open("wb") as handle:
        pickle.dump(bm25, handle)

    model = load_embedding_model()
    embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    vectors = np.asarray(embeddings, dtype="float32")
    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)
    faiss.write_index(index, str(output_dir / "faiss_index.bin"))

    metadata = {
        "embedding_model": MODEL_NAME,
        "embedding_dimension": int(vectors.shape[1]),
        "document_count": len(ids),
    }
    (output_dir / "index_ids.json").write_text(json.dumps(ids, indent=2), encoding="utf-8")
    (output_dir / "index_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print(f"Built retriever artifacts for {len(records)} standards in {output_dir}")


if __name__ == "__main__":
    main()
