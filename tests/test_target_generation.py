import pytest

from news_contracts.storage import ContractStore
from news_contracts.validation import ContractError, validate_target
from target_generation import StubPriceLookup, StubTargetProposer, propose_targets
from target_generation.core import _derive_target_id


def confirmed_thesis(**overrides):
    thesis = {
        "id": "thesis-ai-server-1",
        "body": "AI server power module shortages are likely to push urgent orders toward qualified A-share suppliers.",
        "source_signal_ids": ["sig-ai-server-1"],
        "substantive_claims": [
            {
                "text": "AI server backlog expanded and power module lead times lengthened.",
                "source_signal_ids": ["sig-ai-server-1"],
            }
        ],
        "direction": "bullish",
        "origin_market": "global",
        "target_market": "CN-A",
        "transmission_path": [
            {
                "description": "Global AI server bottleneck can transmit to A-share power module suppliers.",
                "source_signal_ids": ["sig-ai-server-1"],
            }
        ],
        "status": "confirmed",
        "confidence": "medium",
        "uncertainty_tags": [],
        "completeness_critique": {
            "notes": ["Check whether ODMs, power modules, or thermal suppliers capture the bottleneck first."],
            "candidate_thesis_ids": [],
            "body_unchanged": True,
        },
        "adversarial_falsification": {
            "reviewer": "skeptic-reviewer",
            "review_session": {
                "thesis_author_id": "author-agent-1",
                "author_persona": "synthesis-author",
                "reviewer_instance_id": "reviewer-agent-1",
                "reviewer_persona": "skeptic-reviewer",
                "review_run_id": "review-ai-server-1",
            },
            "strongest_counterargument": "The shortage may already be reflected in supplier valuations.",
            "hedge_variables": ["order conversion", "price move since signal"],
        },
        "track_record": {
            "direction": "bullish",
            "falsifiable_expectation": "Within 90 days, qualified suppliers disclose higher AI server related orders.",
            "verification_window": {"start": "2026-06-09", "end": "2026-09-07"},
            "created_at": "2026-06-09T08:00:00Z",
        },
    }
    thesis.update(overrides)
    return thesis


def qualified_candidate(**overrides):
    candidate = {
        "id": "target-power-1",
        "symbol": "300001.SZ",
        "name": "Power Module Supplier",
        "target_market": "CN-A",
        "eligible": True,
        "logic_score": {
            "score": 82,
            "rationale": "Supplier qualification matches the AI server power bottleneck thesis.",
        },
        "buy_point": {
            "status": "neutral",
            "rationale": "Theme is visible but not fully priced after the signal.",
        },
        "state": "buy-zone",
        "catalysts": [
            {
                "kind": "event",
                "value": "order_disclosure",
                "description": "AI server order disclosure or supplier qualification update.",
            }
        ],
        "exit_triggers": [
            {"description": "No order conversion appears before the verification window closes."}
        ],
    }
    candidate.update(overrides)
    return candidate


def test_target_generation_persists_watch_target_from_confirmed_thesis(tmp_path):
    store = ContractStore(tmp_path / "contracts.db")
    thesis = confirmed_thesis()
    store.add_thesis(thesis)

    result = propose_targets(
        thesis,
        StubTargetProposer([qualified_candidate()]),
        StubPriceLookup({"300001.SZ": 0.08}),
        store,
        period="2026-W24",
    )

    expected_id = _derive_target_id("300001.SZ", "thesis-ai-server-1")
    assert result.target_ids == [expected_id]
    assert result.empty_recommendation is None
    target = result.targets[0]
    assert target["state"] == "watch"
    assert target["thesis_ids"] == ["thesis-ai-server-1"]
    assert target["logic_score"]["score"] == 82
    assert target["buy_point"]["price_change_since_signal"] == 0.08
    assert target["priced_in"]["risk"] == "low"
    assert validate_target(target, confirmed_thesis_ids={"thesis-ai-server-1"}).accepted is True
    row = store.connection.execute("select state from targets where id = ?", (expected_id,)).fetchone()
    assert row["state"] == "watch"


def test_target_generation_unfavorable_buy_point_is_not_buy_zone(tmp_path):
    store = ContractStore(tmp_path / "contracts.db")
    thesis = confirmed_thesis()
    store.add_thesis(thesis)
    candidate = qualified_candidate(
        id="target-expensive-1",
        symbol="300002.SZ",
        buy_point={
            "status": "unfavorable",
            "rationale": "The candidate already rallied hard after the signal.",
        },
        state="buy-zone",
    )

    result = propose_targets(
        thesis,
        StubTargetProposer([candidate]),
        StubPriceLookup({"300002.SZ": 0.34}),
        store,
    )

    target = result.targets[0]
    assert target["state"] == "watch"
    assert target["buy_point"]["status"] == "unfavorable"
    assert target["priced_in"]["risk"] == "high"
    assert validate_target(target, confirmed_thesis_ids={"thesis-ai-server-1"}).accepted is True


def test_target_generation_empty_recommendation_when_no_candidate_qualifies(tmp_path):
    store = ContractStore(tmp_path / "contracts.db")
    thesis = confirmed_thesis()
    store.add_thesis(thesis)
    low_quality = qualified_candidate(
        symbol="300003.SZ",
        eligible=False,
        logic_score={"score": 35, "rationale": "Weak link to the thesis."},
    )

    result = propose_targets(
        thesis,
        StubTargetProposer([low_quality]),
        StubPriceLookup({"300003.SZ": 0.01}),
        store,
        period="2026-W24",
    )

    assert result.target_ids == []
    assert result.empty_recommendation == {
        "kind": "empty_recommendation",
        "period": "2026-W24",
        "targets": [],
        "reasons": ["300003.SZ: candidate not eligible"],
    }
    count = store.connection.execute("select count(*) as count from targets").fetchone()["count"]
    assert count == 0


def test_target_generation_empty_recommendation_when_price_lookup_missing(tmp_path):
    store = ContractStore(tmp_path / "contracts.db")
    thesis = confirmed_thesis()
    store.add_thesis(thesis)

    result = propose_targets(
        thesis,
        StubTargetProposer([qualified_candidate(symbol="300004.SZ")]),
        StubPriceLookup({}),
        store,
    )

    assert result.target_ids == []
    assert "missing price change for 300004.SZ" in result.empty_recommendation["reasons"]
    count = store.connection.execute("select count(*) as count from targets").fetchone()["count"]
    assert count == 0


def test_target_generation_rejects_unconfirmed_thesis_linkage(tmp_path):
    store = ContractStore(tmp_path / "contracts.db")
    draft = confirmed_thesis(id="thesis-draft-1", status="draft")
    draft.pop("completeness_critique")
    draft.pop("adversarial_falsification")
    draft.pop("track_record")
    store.add_thesis(draft)

    with pytest.raises(ContractError, match="confirmed thesis"):
        propose_targets(
            draft,
            StubTargetProposer([qualified_candidate(id="target-draft-1")]),
            StubPriceLookup({"300001.SZ": 0.08}),
            store,
        )

    count = store.connection.execute("select count(*) as count from targets").fetchone()["count"]
    assert count == 0


def test_target_generation_ignores_model_candidate_id(tmp_path):
    store = ContractStore(tmp_path / "contracts.db")
    thesis = confirmed_thesis()
    store.add_thesis(thesis)
    candidate = qualified_candidate(id="candidate-1", symbol="300001.SZ")

    result = propose_targets(
        thesis,
        StubTargetProposer([candidate]),
        StubPriceLookup({"300001.SZ": 0.08}),
        store,
    )

    expected_id = _derive_target_id("300001.SZ", "thesis-ai-server-1")
    assert result.target_ids == [expected_id]
    assert result.targets[0]["id"] == expected_id
    assert result.targets[0]["id"] != "candidate-1"


def test_target_generation_same_model_id_across_theses_does_not_collide(tmp_path):
    store = ContractStore(tmp_path / "contracts.db")
    thesis_a = confirmed_thesis(id="thesis-ai-server-1")
    thesis_b = confirmed_thesis(id="thesis-edge-ai-2")
    store.add_thesis(thesis_a)
    store.add_thesis(thesis_b)
    candidate_a = qualified_candidate(id="candidate-1", symbol="300001.SZ")
    candidate_b = qualified_candidate(id="candidate-1", symbol="300001.SZ")

    result_a = propose_targets(
        thesis_a,
        StubTargetProposer([candidate_a]),
        StubPriceLookup({"300001.SZ": 0.08}),
        store,
    )
    result_b = propose_targets(
        thesis_b,
        StubTargetProposer([candidate_b]),
        StubPriceLookup({"300001.SZ": 0.11}),
        store,
    )

    assert result_a.target_ids == [_derive_target_id("300001.SZ", "thesis-ai-server-1")]
    assert result_b.target_ids == [_derive_target_id("300001.SZ", "thesis-edge-ai-2")]
    assert result_a.target_ids[0] != result_b.target_ids[0]
    count = store.connection.execute("select count(*) as count from targets").fetchone()["count"]
    assert count == 2


def test_target_generation_skips_duplicate_symbol_within_one_thesis(tmp_path):
    store = ContractStore(tmp_path / "contracts.db")
    thesis = confirmed_thesis()
    store.add_thesis(thesis)
    first = qualified_candidate(id="candidate-1", symbol="300001.SZ")
    duplicate = qualified_candidate(
        id="candidate-2",
        symbol="300001.SZ",
        logic_score={"score": 95, "rationale": "Duplicate stronger rationale should still be skipped."},
    )

    result = propose_targets(
        thesis,
        StubTargetProposer([first, duplicate]),
        StubPriceLookup({"300001.SZ": 0.08}),
        store,
    )

    assert result.target_ids == [_derive_target_id("300001.SZ", "thesis-ai-server-1")]
    assert result.rejected_reasons == ["300001.SZ: duplicate symbol in thesis"]
    count = store.connection.execute("select count(*) as count from targets").fetchone()["count"]
    assert count == 1


def test_target_generation_drops_null_catalyst_metadata_before_validation(tmp_path):
    store = ContractStore(tmp_path / "contracts.db")
    thesis = confirmed_thesis()
    store.add_thesis(thesis)
    candidate = qualified_candidate(
        id="candidate-null-catalyst",
        symbol="300001.SZ",
        catalysts=[
            {
                "kind": None,
                "value": None,
                "description": "Customer order disclosure validates AI server demand.",
            }
        ],
        exit_triggers=[
            {
                "kind": None,
                "description": "No customer order disclosure before the verification window closes.",
            }
        ],
    )

    result = propose_targets(
        thesis,
        StubTargetProposer([candidate]),
        StubPriceLookup({"300001.SZ": 0.08}),
        store,
    )

    target = result.targets[0]
    assert target["catalysts"] == [
        {"description": "Customer order disclosure validates AI server demand."}
    ]
    assert target["exit_triggers"] == [
        {"description": "No customer order disclosure before the verification window closes."}
    ]
    assert validate_target(target, confirmed_thesis_ids={"thesis-ai-server-1"}).accepted is True


def test_target_generation_preserves_non_null_catalyst_metadata(tmp_path):
    store = ContractStore(tmp_path / "contracts.db")
    thesis = confirmed_thesis()
    store.add_thesis(thesis)
    candidate = qualified_candidate(
        id="candidate-event-catalyst",
        symbol="300001.SZ",
        catalysts=[
            {
                "kind": "event",
                "value": "order_disclosure",
                "description": "Customer order disclosure validates AI server demand.",
            }
        ],
    )

    result = propose_targets(
        thesis,
        StubTargetProposer([candidate]),
        StubPriceLookup({"300001.SZ": 0.08}),
        store,
    )

    assert result.targets[0]["catalysts"] == [
        {
            "kind": "event",
            "value": "order_disclosure",
            "description": "Customer order disclosure validates AI server demand.",
        }
    ]
