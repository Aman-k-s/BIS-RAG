# Codebase Guide

## 1. Final repository structure

- `inference.py`: official batch entry point for hackathon evaluation
- `eval_script.py`: root-level evaluator script matching the organizer format
- `setup.py`: one-time artifact builder
- `demo_query.py`: interactive query runner for demo/debugging
- `requirements.txt`: Python dependencies
- `.env.example`: API key template
- `src/ingest.py`: PDF parsing and standard extraction
- `src/indexer.py`: embedding, FAISS, and BM25 artifact creation
- `src/retriever.py`: hybrid search
- `src/disambiguator.py`: part-specific BIS rules
- `src/reranker.py`: score adjustments for tricky cases
- `src/generator.py`: LangChain-based LLM rationale generation
- `src/pipeline.py`: orchestrates the full RAG flow
- `src/synonyms.py`: domain query expansion
- `data/dataset.pdf`: official BIS source document
- `data/public_test_set.json`: organizer public validation set
- `data/sample_output.json`: organizer reference output shape
- `data/BIS Standards Recommendation Engine_ Hackathon.pdf`: rulebook/spec

## 2. End-to-end flow

### Step A. Build artifacts

Run:

```bash
python setup.py
```

This does two jobs:

1. `src/ingest.py`
   - opens `data/dataset.pdf`
   - finds BIS entries beginning with `SUMMARY OF`
   - extracts a structured record for each standard
   - writes `data/standards_db.json`

2. `src/indexer.py`
   - reads `standards_db.json`
   - builds embeddings with `all-MiniLM-L6-v2`
   - stores dense vectors in `FAISS`
   - builds `BM25` sparse index
   - writes:
     - `data/faiss_index.bin`
     - `data/bm25_index.pkl`
     - `data/index_ids.json`
     - `data/index_metadata.json`

### Step B. Run inference

Run:

```bash
python inference.py --input data/public_test_set.json --output data/results.json
```

For each query:

1. `src/retriever.py`
   - expands query terms using `src/synonyms.py`
   - runs FAISS dense retrieval
   - runs BM25 keyword retrieval
   - merges them using reciprocal rank fusion

2. `src/disambiguator.py`
   - resolves BIS-specific ambiguities such as:
     - `IS 1489 Part 1` vs `Part 2`
     - `IS 2185 Part 1` vs `Part 2`

3. `src/reranker.py`
   - boosts or penalizes candidates using query-aware rules
   - improves final ordering for MRR

4. `src/generator.py`
   - uses Groq or Gemini via LangChain when available
   - generates grounded rationale from retrieved candidates only

5. `src/pipeline.py`
   - combines all steps
   - returns retrieved standards, rationale, LLM info, and timing breakdown

### Step C. Evaluate

Run:

```bash
python eval_script.py --results data/results.json
```

Metrics:

- `Hit Rate@3`: correct answer appears anywhere in top 3
- `MRR@5`: rewards getting the correct answer earlier in the ranking
- `Avg Latency`: average total query time

## 3. Which file does what

### `setup.py`

Bootstrap script. Use this first on a fresh machine.

### `inference.py`

Judge-facing batch runner. Reads input JSON, runs pipeline, writes output JSON, and prints metrics if expected labels are present.

### `demo_query.py`

Human-facing runner. Good for manual testing. Lets you type a query, optionally provide expected standards, and inspect the full breakdown.

### `src/ingest.py`

Turns the raw BIS PDF into structured machine-usable records.

### `src/indexer.py`

Builds retrieval artifacts from structured records.

### `src/retriever.py`

Core search logic. Combines semantic retrieval and keyword retrieval.

### `src/disambiguator.py`

Hard-coded BIS rules for near-duplicate standards.

### `src/reranker.py`

Final score tuning so the best candidate reaches rank 1 more often.

### `src/generator.py`

LLM layer. Uses LangChain and API keys from `.env`.

### `src/pipeline.py`

Main application pipeline. This is the best backend entry point for a future web app.

### `src/synonyms.py`

Maps user/business phrasing to BIS phrasing.

## 4. Best backend entry point for web app

For your web app, do not call `inference.py` directly from the backend.

Use:

- `src.pipeline.BISPipeline`

Recommended backend pattern:

1. Create one `BISPipeline` instance at server startup
2. Reuse it across requests
3. Send user query into `pipeline.run(query)`
4. Return:
   - top standards
   - rationale
   - latency breakdown
   - LLM status

## 5. Suggested next web-app split

- Backend:
  - FastAPI or Flask
  - wraps `BISPipeline`
- Frontend:
  - modern React/Next.js or plain React + Vite
  - query box
  - ranked results
  - rationale card
  - latency/metrics panel

## 6. Submission-safe command sequence

```bash
python setup.py
python inference.py --input data/public_test_set.json --output data/results.json
python eval_script.py --results data/results.json
```
