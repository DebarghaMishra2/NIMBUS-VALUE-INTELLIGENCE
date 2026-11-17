from __future__ import annotations

import asyncio
import math

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

import app.assistant as assistant
import app.main as main


def test_json_safe_handles_pandas_numpy_nan_and_datetime():
    payload = {
        "float_nan": float("nan"),
        "float_inf": float("inf"),
        "numpy_nan": np.float64("nan"),
        "numpy_int": np.int64(7),
        "numpy_bool": np.bool_(True),
        "pandas_na": pd.NA,
        "pandas_nat": pd.NaT,
        "timestamp": pd.Timestamp("2026-11-15T00:00:00Z"),
        "nested": [{"missing": np.float64("nan")}],
    }
    safe = main._json_safe(payload)
    assert safe["float_nan"] is None
    assert safe["float_inf"] is None
    assert safe["numpy_nan"] is None
    assert safe["numpy_int"] == 7
    assert safe["numpy_bool"] is True
    assert safe["pandas_na"] is None
    assert safe["pandas_nat"] is None
    assert safe["timestamp"] == "2026-11-15T00:00:00+00:00"
    assert safe["nested"][0]["missing"] is None


def test_chat_api_returns_200_for_attention_query_on_both_datasets():
    client = TestClient(main.app)
    for dataset_id in ("nimbus_8", "nimbus_40"):
        response = client.post(
            "/api/chat",
            json={
                "dataset_id": dataset_id,
                "as_of_date": "2026-11-15",
                "question": "Which initiatives require attention?",
            },
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["intent"] == "analytics"
        assert data["metrics"]
        assert "Matching initiatives" in data["answer"]
        assert data["dataset_id"] == dataset_id



def test_main_application_endpoints_smoke_for_scale_dataset():
    client = TestClient(main.app)
    params = {"dataset_id": "nimbus_40", "as_of_date": "2026-11-15"}
    checks = [
        ("get", "/", None),
        ("get", "/api/health", None),
        ("get", "/api/datasets", None),
        ("get", "/api/portfolio", params),
        ("get", "/api/scorecard", params),
        ("get", "/api/data-quality", params),
        ("get", "/api/assumptions", None),
        ("get", "/api/charters", params),
        ("get", "/api/weekly-report", params),
        ("get", "/api/download/scorecard.csv", params),
        ("get", "/api/download/change-log.csv", params),
        ("get", "/api/download/weekly-report.md", params),
    ]
    for method, path, query in checks:
        response = client.request(method.upper(), path, params=query)
        assert response.status_code == 200, f"{path}: {response.status_code} {response.text[:300]}"


def test_chat_api_sanitizes_non_finite_values(monkeypatch):
    async def fake_answer_question(question, bundle):
        return {
            "answer": "Test response",
            "intent": "analytics",
            "metrics": [{"initiative_id": "INIT-001", "roi": float("nan"), "adoption": np.float64("inf")}],
            "sources": [],
            "recommendations": [],
            "fallback": False,
            "generation_mode": "deterministic-grounded",
            "llm_status": "not_configured",
        }

    monkeypatch.setattr(main, "answer_question", fake_answer_question)
    response = TestClient(main.app).post(
        "/api/chat",
        json={"dataset_id": "nimbus_8", "as_of_date": "2026-11-15", "question": "ROI for INIT-001?"},
    )
    assert response.status_code == 200, response.text
    metrics = response.json()["metrics"][0]
    assert metrics["roi"] is None
    assert metrics["adoption"] is None


def test_llm_only_may_repeat_initiative_id_from_retrieved_charter(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": "The INIT-005 charter identifies legacy integration and customer hand-offs as risks."}}]}

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr(assistant, "LLM_API_KEY", "test-key")
    monkeypatch.setattr(assistant, "LLM_BASE_URL", "https://example.test/v1")
    monkeypatch.setattr(assistant, "LLM_MODEL", "test-model")
    monkeypatch.setattr(assistant.httpx, "AsyncClient", FakeAsyncClient)

    result, status = asyncio.run(
        assistant._optional_llm(
            question="What risks are documented for INIT-005?",
            intent="narrative",
            base_answer="retrieved source summary",
            metrics=[],
            sources=[{"type": "charter", "initiative_id": "INIT-005", "source_filename": "customer_service_chatbot_charter.md", "section": "Risks and Mitigations", "excerpt": "Legacy integration and customer hand-offs", "citation": "charter — Risks and Mitigations"}],
        )
    )
    assert status == "used"
    assert result and "INIT-005" in result



def test_chat_api_uses_mocked_llm_for_grounded_hybrid_response(monkeypatch):
    async def fake_llm(question, intent, base_answer, metrics, sources):
        assert intent == "hybrid"
        assert metrics
        assert any(source.get("type") == "charter" for source in sources)
        return (
            "INIT-005 shows negative financial performance despite relatively strong adoption. "
            "Its charter identifies legacy-system integration costs and customer hand-offs as risks.",
            "used",
        )

    monkeypatch.setattr(assistant, "_optional_llm", fake_llm)
    response = TestClient(main.app).post(
        "/api/chat",
        json={
            "dataset_id": "nimbus_8",
            "as_of_date": "2026-11-15",
            "question": "Why is INIT-005 underperforming?",
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["generation_mode"] == "llm-grounded"
    assert data["llm_status"] == "used"
    assert "legacy-system integration" in data["answer"]
    assert data["metrics"]
    assert data["sources"]

def test_llm_health_does_not_expose_api_key():
    response = TestClient(main.app).get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert "llm_key_loaded" in payload
    assert "llm_model" in payload
    assert "gsk_" not in str(payload)
