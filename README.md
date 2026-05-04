# BIS Standards Recommendation Engine

This repository contains a RAG-based BIS standards recommendation system built for the BIS Standards Recommendation Engine hackathon. It ingests the provided BIS building materials PDF, builds a hybrid retrieval stack using FAISS and BM25, supports grounded LLM rationale generation for demo use, and exposes both:

- a strict batch `inference.py` entry point for judge evaluation
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

### Python

Use the same Python interpreter consistently across:

- dependency installation
- `setup.py`
- `inference.py`
- `demo_query.py`
- `uvicorn`

If multiple Python environments are installed on your machine, do not mix them. Most runtime issues in this project happen when packages are installed in one interpreter and commands are run from another.

### Create virtual environment
```bash
python -m venv .venv
```

Activate the virtual environment:

**On Windows:**
```bash
.venv\Scripts\activate
```

**On macOS/Linux:**
```bash
source .venv/bin/activate
```

### Install dependencies

```bash
python -m pip install -r requirements.txt
```

### Build retrieval artifacts

```bash
python setup.py
```

### What `setup.py` does

`setup.py` is the offline preparation step for the system. It does not answer queries directly. Its job is to transform the raw BIS PDF into the structured and indexed artifacts required for fast runtime retrieval.

When you run:

```bash
python setup.py
```

the script performs these steps:

1. Validates that `data/dataset.pdf` exists.
2. Runs `src/ingest.py` to parse the BIS PDF into structured BIS standard records.
3. Writes the parsed output to `data/standards_db.json`.
4. Runs `src/indexer.py` to build:
   - sentence-transformer embeddings
   - FAISS vector index
   - BM25 keyword index
   - metadata files connecting vector rows back to BIS standard IDs

Generated artifacts:

- `data/standards_db.json`
- `data/faiss_index.bin`
- `data/bm25_index.pkl`
- `data/index_ids.json`
- `data/index_metadata.json`

Important behavior:

- if all required artifacts already exist, `setup.py` skips rebuilding
- this makes repeated local runs much faster
- if you want to force a rebuild, delete the generated artifact files and rerun `python setup.py`

When to run `setup.py`:

- on first project setup
- after updating `data/dataset.pdf`
- after changing parsing logic in `src/ingest.py`
- after changing indexing logic in `src/indexer.py`

When you usually do not need to rerun it:

- after UI-only changes
- after README changes
- after changing only rationale presentation logic
- after changing only output formatting in `inference.py`

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

## 6. Inference

```bash
python inference.py --input data/public_test_set.json --output data/results.json
```

`inference.py` writes the judge-safe output format:

- `id`
- `query`
- `expected_standards`
- `retrieved_standards`
- `latency_seconds`

Important design note:

- `inference.py` is retrieval-only for latency stability
- LLM calls are used for demo/UI rationale, not for judge batch inference

## 7. Evaluation

Use the provided evaluation logic:

```bash
python data/eval_script.py --results data/results.json
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

## 13. Future scope

- Structured standard fingerprinting:
  Rather than embedding only raw text, each BIS standard can be converted into a semi-structured fingerprint containing material type, product form, physical state, application domain, and regulatory scope. A query can be parsed into the same dimensions and scored using dimensional overlap along with semantic similarity. This is especially valuable for closely related families such as `IS 2185 Part 1`, `Part 2`, and `Part 3`.
- MSE-tuned query normalization:
  A curated mapping layer can translate small-business product language into official BIS terminology before retrieval.
- Compliance-chain reasoning:
  The system can be extended to surface companion standards when one standard depends on another, turning the tool into a more complete compliance advisor.
- Contrastive explanation:
  The rationale layer can explain why the top result was chosen over the runner-up to improve transparency and manual judge confidence.
- Stronger confidence-aware abstention:
  The current confidence gate can be calibrated further so uncertain cases return fewer standards instead of filling the list with weak matches.
- Additional performance engineering:
  Warm-up strategies, repeated-query caching, quantized embedding inference, and smarter LLM retry policies can reduce latency in larger-scale deployments.

## 14. Recommended final submission command sequence

```bash
python setup.py
python inference.py --input data/public_test_set.json --output data/results.json
python data/eval_script.py --results data/results.json
```
