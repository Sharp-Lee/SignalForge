from datetime import UTC, datetime

import pytest

from analysis_orchestration import (
    AnalysisOrchestrationError,
    AnalysisSkipped,
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


def investment_reasoning_response(**overrides):
    audit = {
        "source_signal_ids": ["sig-ai-server-1"],
        "primary_logic_type": "supply_demand",
        "secondary_logic_types": ["margin_spread_repricing"],
        "evidence_status": "accepted",
        "premise": "AI server power module lead-time extension may indicate a supply-demand bottleneck.",
        "upward_validation": [
            {
                "question": "Is the signal grounded in a concrete operational delta?",
                "answer": "The signal reports a 25% backlog expansion and lead-time extension.",
                "evidence": ["sig-ai-server-1"],
                "status": "supported",
            }
        ],
        "transmission_chain": [
            "AI server backlog -> power module lead-time extension -> qualified supplier order leverage"
        ],
        "downstream_decomposition": [
            "Separate ODMs, power module suppliers, thermal suppliers, and component bottlenecks."
        ],
        "chokepoint_candidates": [
            {"node": "服务器电源HVDC", "reason": "Power delivery can become a constrained AI server layer."}
        ],
        "target_search_decision": {
            "status": "allowed",
            "reason": "Evidence is accepted and downstream bottleneck candidates are identified.",
        },
        "missing_evidence": ["Supplier-level order conversion"],
        "disconfirming_evidence": ["Lead times normalize", "AI server backlog reverses"],
        "public_caveat": "这是一条供需观察逻辑，仍取决于订单转化和交期是否继续紧张。",
    }
    audit.update(overrides)
    return audit


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
            "investment_reasoning": investment_reasoning_response(),
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
    assert result.investment_reasoning["primary_logic_type"] == "supply_demand"
    assert result.thesis["investment_reasoning"]["evidence_status"] == "accepted"
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
            "investment_reasoning": investment_reasoning_response(),
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


def test_analysis_orchestration_weak_reasoning_stops_before_free_generation(tmp_path):
    store = ContractStore(tmp_path / "contracts.db")
    signal = realistic_signal()
    author = StubReasoner(
        ReasonerIdentity(instance_id="author-agent-1", persona="synthesis-author"),
        {
            "investment_reasoning": investment_reasoning_response(
                evidence_status="weak",
                target_search_decision={"status": "not_ready", "reason": "Only one signal and missing order conversion."},
                missing_evidence=["Order conversion"],
            ),
            "free_generation": {"body": "should not be called"},
        },
    )

    with pytest.raises(AnalysisSkipped) as exc_info:
        analyze([signal], author, reviewer_reasoner(), store)

    assert exc_info.value.evidence_status == "weak"
    assert [call["role"] for call in author.calls] == ["investment_reasoning"]
    assert store.connection.execute("select count(*) as count from theses").fetchone()["count"] == 0


def test_analysis_orchestration_rejected_reasoning_stops_before_free_generation(tmp_path):
    store = ContractStore(tmp_path / "contracts.db")
    signal = realistic_signal()
    author = StubReasoner(
        ReasonerIdentity(instance_id="author-agent-1", persona="synthesis-author"),
        {
            "investment_reasoning": investment_reasoning_response(
                evidence_status="rejected",
                target_search_decision={"status": "blocked", "reason": "Generic product commentary."},
                missing_evidence=["No measurable delta"],
            ),
            "free_generation": {"body": "should not be called"},
        },
    )

    with pytest.raises(AnalysisSkipped) as exc_info:
        analyze([signal], author, reviewer_reasoner(), store)

    assert exc_info.value.evidence_status == "rejected"
    assert [call["role"] for call in author.calls] == ["investment_reasoning"]
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
