from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from inference import ensure_artifacts, evaluate_results
from src.pipeline import BISPipeline


class QueryRequest(BaseModel):
    query: str
    expected_standard: Optional[str] = None


ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "web"

ensure_artifacts(ROOT)
pipeline = BISPipeline(ROOT / "data")

app = FastAPI(title="BIS Standards Recommendation Engine", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/assets", StaticFiles(directory=STATIC_DIR), name="assets")


@app.get("/")
def serve_index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/query")
def run_query(payload: QueryRequest) -> dict[str, object]:
    result = pipeline.run(payload.query)
    expected_standards = [payload.expected_standard] if payload.expected_standard else []

    response = {
        "query": payload.query,
        "expected_standards": expected_standards,
        "retrieved_standards": result["retrieved_standards"],
        "match_decision": result["match_decision"],
        "top_candidates": result["top_candidates"],
        "rationale": result["rationale"],
        "llm": result["llm"],
        "timing_breakdown_seconds": result["timing_breakdown_seconds"],
        "latency_seconds": result["latency_seconds"],
    }
    metrics = evaluate_results(
        [
            {
                "id": "web-query",
                "expected_standards": expected_standards,
                "retrieved_standards": result["retrieved_standards"],
                "latency_seconds": result["latency_seconds"],
            }
        ]
    )
    return {"result": response, "metrics": metrics}
