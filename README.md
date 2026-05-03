# BIS Standards Recommendation Engine

This repository contains a LangChain-based RAG pipeline for the BIS building materials hackathon. It parses the provided BIS PDF, builds FAISS and BM25 retrieval artifacts, and produces ranked standard recommendations in the JSON format required by the organizers.

## Repository layout

- `inference.py`: judge entry point
- `setup.py`: builds parsed records and retrieval artifacts from `data/dataset.pdf`
- `src/ingest.py`: PDF parser
- `src/indexer.py`: sentence-transformer embeddings, FAISS, and BM25 artifact builder
- `src/retriever.py`: hybrid dense+sparse retrieval and rank fusion
- `src/reranker.py`: query-aware heuristic reranking
- `src/disambiguator.py`: part-level disambiguation rules
- `src/generator.py`: LangChain LLM wrapper for grounded rationale generation
- `src/pipeline.py`: runtime orchestration
- `eval_script.py`: root-level evaluation script for hackathon scoring
- `CODEBASE_GUIDE.md`: step-by-step structure and file responsibilities

## Usage

Build artifacts:

```bash
python setup.py
```

Run inference:

```bash
python inference.py --input data/public_test_set.json --output data/results.json
```

Evaluate:

```bash
python eval_script.py --results data/results.json
```

Run a single demo query with rationale:

```bash
python demo_query.py --query "We are manufacturing 33 Grade Ordinary Portland Cement. Which BIS standard applies?"
```

Enable a real LLM:

```bash
copy .env.example .env
```

Then set either `GROQ_API_KEY` or `GOOGLE_API_KEY` in `.env`.

Read the architecture walkthrough:

```bash
CODEBASE_GUIDE.md
```

## Notes

- The pipeline is optimized for the provided BIS `SP 21` style summaries in `data/dataset.pdf`.
- `inference.py` auto-runs `setup.py` if the retrieval artifacts are missing.
- If `GROQ_API_KEY` or `GOOGLE_API_KEY` is set, the pipeline uses a LangChain chat model to generate grounded rationales. Retrieval outputs are always taken from the indexed standards database, never from the LLM.
- `inference.py` intentionally writes only the fields required by the hackathon evaluator. Use `demo_query.py` to see the LLM-backed rationale and ranked candidates.
