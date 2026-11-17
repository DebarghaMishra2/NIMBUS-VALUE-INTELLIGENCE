from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
import io
import json
import logging
import math
import numpy as np
import pandas as pd
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from .config import (FRONTEND_DIR, DEFAULT_AS_OF_DATE, DATASETS, STORAGE_DIR,
                     LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, LLM_MISSING_SETTINGS,
                     LLM_CONFIGURED, EMBEDDING_BACKEND)
from .engine import manager
from .assistant import answer_question
from .reports import build_weekly_report
from .utils import parse_date

logger = logging.getLogger(__name__)

app = FastAPI(title="Nimbus Group AI Value Intelligence Assistant", version="1.0.1",
              description="HCLTech Future Ready AI Engineer Hackathon - Enterprise RAG Value Intelligence Assistant")
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

class IngestRequest(BaseModel):
    dataset_id: str = Field(default="nimbus_8")
    as_of_date: str = Field(default=DEFAULT_AS_OF_DATE)
    force_rebuild: bool = False

class ChatRequest(BaseModel):
    dataset_id: str = Field(default="nimbus_8")
    as_of_date: str = Field(default=DEFAULT_AS_OF_DATE)
    question: str = Field(min_length=2, max_length=2000)


def _bundle(dataset_id: str, as_of_date: str | None = None, force: bool = False):
    try:
        return manager.load(dataset_id, as_of_date, force)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _json_safe(value):
    """Recursively convert app data into strict JSON-compatible values.

    FastAPI's default JSON encoder rejects NaN/Infinity and does not handle every
    NumPy/Pandas scalar. Missing numeric values are emitted as JSON null, never 0.
    """
    if value is None or value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]
    if isinstance(value, np.ndarray):
        return [_json_safe(v) for v in value.tolist()]
    if isinstance(value, (pd.Series,)):
        return [_json_safe(v) for v in value.tolist()]
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Decimal):
        number = float(value)
        return number if math.isfinite(number) else None
    if isinstance(value, np.generic):
        return _json_safe(value.item())
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    # Catch scalar pandas missing values from extension dtypes.
    try:
        missing = pd.isna(value)
        if isinstance(missing, (bool, np.bool_)) and bool(missing):
            return None
    except (TypeError, ValueError):
        pass
    # Keep simple JSON primitives unchanged; stringify uncommon objects rather
    # than allowing a late response-serialization failure to turn a chat into 500.
    if isinstance(value, (str,)):
        return value
    return str(value)


def _records(df: pd.DataFrame):
    return _json_safe(df.to_dict(orient="records"))

@app.get("/", include_in_schema=False)
def home():
    return FileResponse(FRONTEND_DIR / "index.html")

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "app": "Nimbus Group AI Value Intelligence Assistant",
        "llm_enabled": LLM_CONFIGURED,
        "llm_configured": LLM_CONFIGURED,
        "llm_key_loaded": bool(LLM_API_KEY),
        "llm_base_url_configured": bool(LLM_BASE_URL),
        "llm_model": LLM_MODEL or None,
        "llm_missing_settings": LLM_MISSING_SETTINGS,
        "embedding_backend_config": EMBEDDING_BACKEND,
    }


@app.get("/api/llm/test")
async def llm_test():
    """Send a tiny test prompt to the configured provider without exposing secrets."""
    if not LLM_CONFIGURED:
        return {"ok": False, "configured": False, "missing_settings": LLM_MISSING_SETTINGS}
    payload = {
        "model": LLM_MODEL,
        "temperature": 0.1,
        "messages": [{"role": "user", "content": "Reply exactly: LLM_CONNECTION_OK"}],
    }
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"{LLM_BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {LLM_API_KEY}", "Content-Type": "application/json"},
                json=payload,
            )
            response.raise_for_status()
            answer = response.json()["choices"][0]["message"]["content"].strip()
            return {"ok": bool(answer), "configured": True, "model": LLM_MODEL,
                    "response": answer[:300]}
    except httpx.HTTPStatusError as exc:
        return {"ok": False, "configured": True, "model": LLM_MODEL,
                "http_status": exc.response.status_code,
                "error": exc.response.text[:600]}
    except httpx.TimeoutException:
        return {"ok": False, "configured": True, "model": LLM_MODEL,
                "error": "Provider request timed out. Check connectivity and provider status."}
    except Exception as exc:
        return {"ok": False, "configured": True, "model": LLM_MODEL,
                "error": f"{type(exc).__name__}: {str(exc)[:400]}"}

@app.get("/api/datasets")
def datasets():
    return {"datasets": manager.available_datasets(), "default_as_of_date": DEFAULT_AS_OF_DATE}

@app.post("/api/ingest")
def ingest(req: IngestRequest):
    bundle = _bundle(req.dataset_id, req.as_of_date, req.force_rebuild)
    return {"status": "ready", "dataset_id": bundle.dataset_id, "as_of_date": bundle.as_of_date,
            "initiative_count": int(len(bundle.scorecard)), "charter_chunks": len(bundle.chunks),
            "change_log_entries": len(bundle.cleaned.change_log),
            "embedding_backend": bundle.retriever.embedding_backend,
            "storage_path": str((STORAGE_DIR / bundle.dataset_id / bundle.as_of_date).relative_to(STORAGE_DIR.parent))}

@app.get("/api/portfolio")
def portfolio(dataset_id: str = "nimbus_8", as_of_date: str = DEFAULT_AS_OF_DATE):
    return _json_safe(_bundle(dataset_id, as_of_date).portfolio)

@app.get("/api/scorecard")
def scorecard(dataset_id: str = "nimbus_8", as_of_date: str = DEFAULT_AS_OF_DATE):
    b = _bundle(dataset_id, as_of_date)
    return {"dataset_id": dataset_id, "as_of_date": b.as_of_date, "rows": _records(b.scorecard)}

@app.get("/api/data-quality")
def data_quality(dataset_id: str = "nimbus_8", as_of_date: str = DEFAULT_AS_OF_DATE):
    b = _bundle(dataset_id, as_of_date)
    logs = b.cleaned.change_log
    by_rule = {}
    for row in logs:
        by_rule[row["rule"]] = by_rule.get(row["rule"], 0) + 1
    return _json_safe({"dataset_id": dataset_id, "entry_count": len(logs), "severity_counts": {
                "info": sum(1 for x in logs if x["severity"] == "info"),
                "warning": sum(1 for x in logs if x["severity"] == "warning"),
                "error": sum(1 for x in logs if x["severity"] == "error")},
            "rule_counts": by_rule, "entries": logs})

@app.get("/api/assumptions")
def assumptions():
    path = Path(__file__).resolve().parents[1] / "docs" / "METRIC_DEFINITIONS_AND_ASSUMPTIONS.md"
    return {"content": path.read_text(encoding="utf-8")}

@app.get("/api/charters")
def charters(dataset_id: str = "nimbus_8", as_of_date: str = DEFAULT_AS_OF_DATE):
    b = _bundle(dataset_id, as_of_date)
    docs = {}
    for c in b.chunks:
        k = (c["initiative_id"], c["source_filename"])
        docs.setdefault(k, {"initiative_id": k[0], "source_filename": k[1], "sections": [], "chunk_count": 0})
        docs[k]["chunk_count"] += 1
        if c["section"] not in docs[k]["sections"]:
            docs[k]["sections"].append(c["section"])
    return {"documents": list(docs.values()), "chunk_count": len(b.chunks), "embedding_backend": b.retriever.embedding_backend}

@app.post("/api/chat")
async def chat(req: ChatRequest):
    try:
        b = _bundle(req.dataset_id, req.as_of_date)
        result = await answer_question(req.question, b)
        result.update({"dataset_id": req.dataset_id, "as_of_date": b.as_of_date})
        return _json_safe(result)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Chat request failed for dataset=%s", req.dataset_id)
        raise HTTPException(
            status_code=500,
            detail="Chat request failed unexpectedly. Check the backend terminal logs for the traceback.",
        ) from exc

@app.get("/api/weekly-report")
def weekly_report(dataset_id: str = "nimbus_8", as_of_date: str = DEFAULT_AS_OF_DATE):
    b = _bundle(dataset_id, as_of_date)
    return {"dataset_id": dataset_id, "as_of_date": b.as_of_date, "report_markdown": build_weekly_report(b)}

@app.get("/api/download/scorecard.csv")
def download_scorecard(dataset_id: str = "nimbus_8", as_of_date: str = DEFAULT_AS_OF_DATE):
    b = _bundle(dataset_id, as_of_date)
    buffer = io.StringIO()
    b.scorecard.to_csv(buffer, index=False)
    buffer.seek(0)
    return StreamingResponse(iter([buffer.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f"attachment; filename={dataset_id}_scorecard_{b.as_of_date}.csv"})

@app.get("/api/download/change-log.csv")
def download_change_log(dataset_id: str = "nimbus_8", as_of_date: str = DEFAULT_AS_OF_DATE):
    b = _bundle(dataset_id, as_of_date)
    buffer = io.StringIO()
    pd.DataFrame(b.cleaned.change_log).to_csv(buffer, index=False)
    buffer.seek(0)
    return StreamingResponse(iter([buffer.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f"attachment; filename={dataset_id}_change_log.csv"})

@app.get("/api/download/weekly-report.md")
def download_weekly_report(dataset_id: str = "nimbus_8", as_of_date: str = DEFAULT_AS_OF_DATE):
    b = _bundle(dataset_id, as_of_date)
    report = build_weekly_report(b)
    return PlainTextResponse(report, headers={"Content-Disposition": f"attachment; filename={dataset_id}_weekly_report_{b.as_of_date}.md"})
