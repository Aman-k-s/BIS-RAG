# BIS Standards Recommendation Engine

This repository contains a RAG system for the BIS Standards Recommendation Engine hackathon. It ingests the provided BIS building materials PDF, builds a hybrid retrieval stack using FAISS and BM25, supports grounded LLM rationale generation, and exposes both:

- a strict batch `inference.py` entry point for judge
- a modern web UI for demo and presentation use

## 1. Submission structure

This repo follows the required hackathon layout:

- `src/`: main application logic
- `data/`: dataset, public test set, sample schema, and generated artifacts
- `inference.py`: mandatory judge entry point
- `requirements.txt`: environment dependencies
- `eval_script.py`: evaluation script
- `presentation.pdf` 

## 2. Repository overview

### Root files

- `setup.py`: builds all retrieval artifacts from `data/dataset.pdf`
- `inference.py`: reads input JSON, runs retrieval, writes the official results JSON
- `eval_script.py`: evaluates result JSON using Hit Rate@3, MRR@5, and latency
- `demo_query.py`: interactive CLI testing with rationale and latency breakdown
- `app.py`: FastAPI backend for the demo web app

### Source files

- `src/ingest.py`: parses the BIS PDF into structured standard records
- `src/indexer.py`: builds sentence-transformer embeddings, FAISS index, and BM25 index
- `src/retriever.py`: hybrid dense+sparse retrieval
- `src/disambiguator.py`: BIS-specific rule fixes for part confusion
- `src/reranker.py`: final ranking adjustments
- `src/generator.py`: LLM rationale generation with hallucination guard
- `src/pipeline.py`: full end-to-end runtime pipeline
- `src/synonyms.py`: query expansion for business-language to BIS-language mapping

### Data files

- `data/dataset.pdf`: official source dataset
- `data/public_test_set.json`: public validation queries
- `data/sample_output.json`: official output example
- `data/BIS Standards Recommendation Engine_ Hackathon.pdf`: rulebook/spec
- `data/standards_db.json`: parsed structured records
- `data/faiss_index.bin`: vector database
- `data/bm25_index.pkl`: keyword index
- `data/index_ids.json`: vector row to standard mapping
- `data/index_metadata.json`: embedding model metadata

## 3. How the system works

### Step 1. Ingestion

`src/ingest.py` reads `data/dataset.pdf`, detects BIS standard entries beginning with `SUMMARY OF`, and extracts:

- standard ID
- year
- part number if present
- title
- scope
- section
- embedding text

This produces `data/standards_db.json`.

### Step 2. Indexing

`src/indexer.py` reads `standards_db.json` and builds:

- dense embeddings with `sentence-transformers/all-MiniLM-L6-v2`
- a FAISS similarity index
- a BM25 sparse keyword index

This creates the retrieval artifacts used at runtime.

### Step 3. Retrieval

`src/retriever.py` performs:

- synonym-based query expansion
- FAISS dense retrieval
- BM25 sparse retrieval
- reciprocal rank fusion to merge both rankings

### Step 4. Post-retrieval ranking

The pipeline then applies:

- `src/disambiguator.py` for BIS-specific part disambiguation
- `src/reranker.py` for score adjustments

### Step 5. Rationale generation

`src/generator.py` sends the retrieved context to an LLM only for explanation, not for retrieving standard IDs.

Important safety rules:

- retrieved standards always come from the indexed BIS dataset
- the LLM never decides the standard IDs directly
- if the LLM mentions a BIS standard not in the retrieved set, a hallucination guard replaces the answer with a safe fallback rationale

## 4. Setup instructions

### Prerequisites

- Python 3.10 or newer (use the same interpreter consistently for install, setup, and run)
- The official BIS dataset PDF placed at `data/dataset.pdf` before running `setup.py`
- Internet access on first run (the embedding model `sentence-transformers/all-MiniLM-L6-v2` is downloaded once and cached locally)

### Step 1 — Create and activate a virtual environment (recommended)

```bash
python -m venv .venv
# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1
# macOS / Linux
source .venv/bin/activate
```

### Step 2 — Install dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Step 3 — Build retrieval artifacts

Make sure `data/dataset.pdf` exists, then run:

```bash
python setup.py
```

This produces `standards_db.json`, `faiss_index.bin`, `bm25_index.pkl`, `index_ids.json`, and `index_metadata.json` inside `data/`. If those files already exist, `setup.py` skips the rebuild.
## 5. API key setup

The project supports:

- Groq
- Gemini

Create your `.env` 

Then fill one or both variables:

```env
GROQ_API_KEY=your_groq_key_here
GOOGLE_API_KEY=your_google_key_here
```

### Groq key

Get a key from:

- https://console.groq.com/
- model docs: https://console.groq.com/docs/models

### Gemini key

Get a key from:

- https://aistudio.google.com/
- docs: https://ai.google.dev/gemini-api/docs/api-key

Important:
- every teammate or judge machine that wants LLM support must create its own local `.env`
- without `.env`, retrieval still works, but LLM rationale falls back to a non-LLM explanation

## 6.inference
```bash
python inference.py --input data/public_test_set.json --output data/results.json
```
`inference.py` writes only the required output format:

- `id`
- `retrieved_standards`
- `latency_seconds`


## 7. Evaluation

Use the provided evaluation logic (the script lives in the repo root):
```bash
python eval_script.py --results data/results.json
```
Metrics:

- `Hit Rate@3`: at least one correct standard appears in top 3
- `MRR@5`: rewards correct answers appearing earlier in the ranking
- `Avg Latency`: average per-query latency from the output JSON

## 8. Interactive CLI demo

Run:
```bash
python demo_query.py --require-llm
```
It will prompt for:

- query
- expected standard (optional)

It shows:

- top candidates
- rationale
- LLM status
- latency breakdown
- optional metrics

## 9. Web app

Start the backend:
```bash
python -m uvicorn app:app --reload
```

Then open:

- http://127.0.0.1:8000

Notes:

- On first launch the app will auto-run `setup.py` if any retrieval artifact under `data/` is missing, so the very first start may take longer.
- Without a `.env` file the app still works — the LLM rationale gracefully falls back to a deterministic explanation.

The web app includes:

- query input
- optional expected standard input
- ranked standards
- LLM rationale
- latency breakdown
- metric cards

## 10. Transparency

### Source of truth

All retrieval and scoring are based on the provided BIS dataset:

- `data/dataset.pdf`

No external knowledge source is used for standard retrieval.

### External APIs used

Only for rationale generation:

- Groq API
- Google Gemini API

These APIs are optional. They do not control the retrieved standard IDs.

### Local indexes

The project builds:

- FAISS vector database
- BM25 keyword index

These are generated from the provided dataset only.

## 11. Hardware expectations

The system is designed to run on standard hardware:

- CPU-only retrieval is supported
- no GPU is required for the current setup
- consumer GPU is optional, not required

The heaviest local step is embedding/index build during `setup.py`. Runtime inference is much lighter.

## 12. Known design decisions

- Batch submission output is intentionally minimal for judge compatibility
- LLM rationale exists for demo, UI, and judge-facing explanation quality
- The pipeline can abstain with `no-confident-match` when retrieval confidence is weak instead of forcing a bad standard

## 13. Recommended final submission command sequence

```bash
python setup.py
python inference.py --input data/public_test_set.json --output data/results.json
python eval_script.py --results data/results.json
```
