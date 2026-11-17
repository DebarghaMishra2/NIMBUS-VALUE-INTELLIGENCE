from pathlib import Path
import asyncio
import pandas as pd
from app.engine import manager
from app.assistant import answer_question, classify_intent
from app.reports import build_weekly_report


def test_scorecard_matches_answer_keys_for_both_datasets():
    for dataset_id in ["nimbus_8", "nimbus_40"]:
        b = manager.load(dataset_id, force=True)
        expected = pd.read_csv(b.dataset_dir / "answer_key/expected_scorecard.csv").set_index("initiative_id").sort_index()
        actual = b.scorecard.set_index("initiative_id").sort_index()
        cols = ["months_live", "adoption", "wau_change", "roi", "avg_monthly_benefit", "payback_months", "run_rate_vs_plan"]
        assert (actual[cols] - expected[cols]).abs().max().max() < 1e-6
        assert (actual.status == expected.status).all()


def test_intent_routing():
    assert classify_intent("What is the ROI for INIT-005?") == "analytics"
    assert classify_intent("What risks are documented for INIT-005?") == "narrative"
    assert classify_intent("Why is INIT-005 underperforming?") == "hybrid"
    assert classify_intent("Which initiatives require attention?") == "analytics"


def test_missing_evidence_and_personal_data_fallback():
    b = manager.load("nimbus_8")
    async def run():
        missing = await answer_question("What risks are documented for INIT-003?", b)
        personal = await answer_question("What is the personal phone number of INIT-001's sponsor?", b)
        assert missing["answer"] == "I do not have that in the data provided."
        assert personal["answer"] == "I do not have that in the data provided."
    asyncio.run(run())


def test_prompt_injection_is_neutralised():
    b = manager.load("nimbus_8")
    joined = " ".join(c["content"].lower() for c in b.chunks if c["initiative_id"] == "INIT-005")
    assert "ignore all previous instructions" not in joined
    assert "250 percent" not in joined


def test_hybrid_answer_uses_metrics_and_charter_sources():
    b = manager.load("nimbus_8")
    async def run():
        out = await answer_question("Why is INIT-005 underperforming?", b)
        assert out["intent"] == "hybrid"
        assert out["metrics"]
        assert any(s.get("type") == "charter" for s in out["sources"])
        attention = await answer_question("Which initiatives require attention?", b)
        assert attention["intent"] == "analytics"
        assert attention["metrics"]
    asyncio.run(run())


def test_weekly_report_has_traceable_sections():
    b = manager.load("nimbus_8")
    report = build_weekly_report(b)
    assert "Weekly AI Portfolio Value Report" in report
    assert "raw/initiatives.csv" in report
    assert "customer_service_chatbot_charter.md" in report


def test_section_aware_charter_retrieval_returns_correct_citation():
    b = manager.load("nimbus_8")
    async def run():
        out = await answer_question("What are the success measures for INIT-008?", b)
        assert not out["fallback"]
        assert any(s.get("source_filename") == "demand_planning_model_charter.pdf" and
                   s.get("section") == "Success Measures" for s in out["sources"])
    asyncio.run(run())
