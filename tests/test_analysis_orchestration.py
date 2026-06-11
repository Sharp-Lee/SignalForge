from datetime import UTC, datetime

import pytest

from analysis_orchestration import (
    AnalysisOrchestrationError,
    ReasonerIdentity,
    StubReasoner,
    analyze,
)
from news_contracts.storage import ContractStore
from news_contracts.validation import ContractError, validate_thesis


def realistic_signal(**overrides):
    signal = {
        "id": "sig-ai-server-1",
        "source": {
            "id": "rss:semis",
            "name": "Global Semis RSS",
            "published_at": "2026-06-09T08:00:00Z",
            "url": "https://example.com/ai-server-supply",
        },
        "title": "AI server backlog expands 25% as power modules tighten",
        "body": "Supplier checks show AI server backlog expanded 25% and power module lead times moved from 6 to 14 weeks.",
        "signal_origin": "news",
        "type_tag": "supply_demand_bottleneck",
        "triage": {"excluded": False, "reasons": [], "strategy": "zh_cn_heuristic_v0"},
        "raw_payload": {
            "source": "rss",
            "feed": "semis",
            "published_at": "2026-06-09T08:00:00Z",
        },
    }
    signal.update(overrides)
    return signal


def author_reasoner(**free_overrides):
    free_generation = {
        "body": "AI server power module shortages are likely to push urgent orders toward qualified Asian suppliers, creating a second-order A-share watch theme.",
        "source_signal_ids": ["sig-ai-server-1"],
        "substantive_claims": [
            {
                "text": "AI server backlog expanded and power module lead times lengthened.",
                "source_signal_ids": ["sig-ai-server-1"],
            }
        ],
        "direction": "bullish",
        "confidence": "medium",
        "uncertainty_tags": [],
        "origin_market": "global",
        "target_market": "CN-A",
        "transmission_path": [
            {
                "description": "Global AI server bottleneck can transmit to A-share power module suppliers.",
                "source_signal_ids": ["sig-ai-server-1"],
            }
        ],
        "falsifiable_expectation": "Within 90 days, qualified suppliers disclose higher AI server related orders.",
        "verification_window": {"start": "2026-06-09", "end": "2026-09-07"},
    }
    free_generation.update(free_overrides)
    return StubReasoner(
        ReasonerIdentity(instance_id="author-agent-1", persona="synthesis-author"),
        {
            "free_generation": free_generation,
            "completeness_critique": {
                "notes": ["Check whether ODMs, power modules, or thermal suppliers capture the bottleneck first."],
                "candidate_thesis_ids": ["candidate-ai-thermal"],
                "body_unchanged": True,
            },
        },
    )


def reviewer_reasoner(**adversarial_overrides):
    adversarial = {
        "reviewer": "skeptic-reviewer",
        "review_run_id": "review-ai-server-1",
        "strongest_counterargument": "The backlog may already be priced into suppliers and order visibility could be double counted.",
        "hedge_variables": ["supplier order conversion", "price move since signal"],
    }
    adversarial.update(adversarial_overrides)
    return StubReasoner(
        ReasonerIdentity(instance_id="reviewer-agent-1", persona="skeptic-reviewer"),
        {"adversarial_falsification": adversarial},
    )


def test_analysis_orchestration_runs_three_steps_and_persists_confirmed_thesis(tmp_path):
    store = ContractStore(tmp_path / "contracts.db")
    signal = realistic_signal()
    store.add_signal(signal)

    result = analyze(
        [signal],
        author_reasoner(),
        reviewer_reasoner(),
        store,
        thesis_id="thesis-ai-server-1",
        created_at=datetime(2026, 6, 9, 8, 0, tzinfo=UTC),
    )

    assert result.thesis_id == "thesis-ai-server-1"
    assert result.thesis["status"] == "confirmed"
    assert result.thesis["completeness_critique"]["body_unchanged"] is True
    assert result.thesis["adversarial_falsification"]["review_session"]["reviewer_instance_id"] == "reviewer-agent-1"
    assert validate_thesis(result.thesis).accepted is True
    row = store.connection.execute("select status from theses where id = ?", (result.thesis_id,)).fetchone()
    assert row["status"] == "confirmed"
    assert store.connection.execute("select count(*) as count from targets").fetchone()["count"] == 0
    assert store.connection.execute("select count(*) as count from track_record").fetchone()["count"] == 1


def test_analysis_orchestration_rejects_same_author_and_reviewer_instance(tmp_path):
    store = ContractStore(tmp_path / "contracts.db")
    signal = realistic_signal()
    same_reviewer = StubReasoner(
        ReasonerIdentity(instance_id="author-agent-1", persona="skeptic-reviewer"),
        {"adversarial_falsification": {}},
    )

    with pytest.raises(AnalysisOrchestrationError, match="reviewer instance"):
        analyze([signal], author_reasoner(), same_reviewer, store)

    assert store.connection.execute("select count(*) as count from theses").fetchone()["count"] == 0


def test_analysis_orchestration_rejects_same_author_and_reviewer_persona(tmp_path):
    store = ContractStore(tmp_path / "contracts.db")
    signal = realistic_signal()
    same_persona = StubReasoner(
        ReasonerIdentity(instance_id="reviewer-agent-2", persona="synthesis-author"),
        {"adversarial_falsification": {}},
    )

    with pytest.raises(AnalysisOrchestrationError, match="reviewer persona"):
        analyze([signal], author_reasoner(), same_persona, store)

    assert store.connection.execute("select count(*) as count from theses").fetchone()["count"] == 0


def test_analysis_orchestration_missing_completeness_critique_does_not_confirm(tmp_path):
    store = ContractStore(tmp_path / "contracts.db")
    signal = realistic_signal()
    author = StubReasoner(
        ReasonerIdentity(instance_id="author-agent-1", persona="synthesis-author"),
        {
            "free_generation": {
                "body": "AI server supply pressure could benefit qualified suppliers.",
                "source_signal_ids": ["sig-ai-server-1"],
            },
            "completeness_critique": {},
        },
    )

    with pytest.raises(AnalysisOrchestrationError, match="completeness critique"):
        analyze([signal], author, reviewer_reasoner(), store)

    assert store.connection.execute("select count(*) as count from theses").fetchone()["count"] == 0


def test_analysis_orchestration_missing_adversarial_review_does_not_confirm(tmp_path):
    store = ContractStore(tmp_path / "contracts.db")
    signal = realistic_signal()
    reviewer = StubReasoner(
        ReasonerIdentity(instance_id="reviewer-agent-1", persona="skeptic-reviewer"),
        {"adversarial_falsification": {}},
    )

    with pytest.raises(AnalysisOrchestrationError, match="strongest_counterargument"):
        analyze([signal], author_reasoner(), reviewer, store)

    assert store.connection.execute("select count(*) as count from theses").fetchone()["count"] == 0


def test_contract_store_still_rejects_confirmed_thesis_missing_required_gates(tmp_path):
    store = ContractStore(tmp_path / "contracts.db")
    thesis = {
        "id": "thesis-missing-gates",
        "body": "A free-form thesis without review gates.",
        "source_signal_ids": ["sig-ai-server-1"],
        "status": "confirmed",
        "confidence": "medium",
        "track_record": {
            "direction": "bullish",
            "falsifiable_expectation": "Order announcements rise within 90 days.",
            "verification_window": {"start": "2026-06-09", "end": "2026-09-07"},
            "created_at": "2026-06-09T08:00:00Z",
        },
    }

    with pytest.raises(ContractError, match="completeness_critique"):
        store.add_thesis(thesis)
