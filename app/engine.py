from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json
import pandas as pd
from .config import DATASETS, STORAGE_DIR, DEFAULT_AS_OF_DATE, EMBEDDING_BACKEND, EMBEDDING_MODEL
from .utils import parse_date
from .cleaning import clean_dataset
from .scorecard import calculate_scorecard, portfolio_summary
from .documents import ingest_charters, persist_chunks
from .retrieval import HybridRetriever

@dataclass
class DatasetBundle:
    dataset_id: str
    as_of_date: str
    dataset_dir: Path
    cleaned: object
    scorecard: pd.DataFrame
    portfolio: dict
    chunks: list[dict]
    retriever: HybridRetriever


class EngineManager:
    def __init__(self):
        self.cache: dict[tuple[str, str], DatasetBundle] = {}

    def available_datasets(self):
        result = []
        for dataset_id, path in DATASETS.items():
            if path.exists():
                result.append({"dataset_id": dataset_id,
                               "label": "8 curated initiatives" if dataset_id == "nimbus_8" else "40 initiatives (8 curated + 32 generated)",
                               "path": str(path.relative_to(path.parents[1])) if path.is_relative_to(path.parents[1]) else dataset_id})
        return result

    def load(self, dataset_id: str, as_of: str | None = None, force: bool = False) -> DatasetBundle:
        if dataset_id not in DATASETS:
            raise ValueError(f"Unknown dataset_id: {dataset_id}")
        as_of = as_of or DEFAULT_AS_OF_DATE
        as_of_dt = parse_date(as_of)
        as_of = as_of_dt.isoformat()
        key = (dataset_id, as_of)
        if key in self.cache and not force:
            return self.cache[key]
        dataset_dir = DATASETS[dataset_id]
        cleaned = clean_dataset(dataset_dir, as_of_dt)
        scorecard = calculate_scorecard(cleaned)
        portfolio = portfolio_summary(scorecard)
        chunks = ingest_charters(dataset_dir, cleaned.initiatives)
        for chunk in chunks:
            chunk["dataset_id"] = dataset_id
        storage_dir = STORAGE_DIR / dataset_id / as_of
        storage_dir.mkdir(parents=True, exist_ok=True)
        cleaned.initiatives.to_csv(storage_dir / "initiatives_clean.csv", index=False)
        cleaned.usage.to_csv(storage_dir / "weekly_usage_clean.csv", index=False)
        cleaned.financials.to_csv(storage_dir / "financials_normalized.csv", index=False)
        scorecard.to_csv(storage_dir / "scorecard.csv", index=False)
        (storage_dir / "change_log.json").write_text(json.dumps(cleaned.change_log, indent=2, default=str), encoding="utf-8")
        (storage_dir / "portfolio_summary.json").write_text(json.dumps(portfolio, indent=2, default=str), encoding="utf-8")
        persist_chunks(chunks, storage_dir / "chunks.jsonl")
        retriever = HybridRetriever(chunks, storage_dir / "retrieval", EMBEDDING_BACKEND, EMBEDDING_MODEL)
        bundle = DatasetBundle(dataset_id, as_of, dataset_dir, cleaned, scorecard, portfolio, chunks, retriever)
        self.cache[key] = bundle
        return bundle

    def invalidate(self, dataset_id: str | None = None):
        if dataset_id:
            self.cache = {k: v for k, v in self.cache.items() if k[0] != dataset_id}
        else:
            self.cache.clear()

manager = EngineManager()
