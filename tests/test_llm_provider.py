import json
import os
import sys
from types import SimpleNamespace

import pytest

from analysis_orchestration import LlmReasoner, ReasonerIdentity, analyze
from llm_provider import (
    ADVERSARIAL_SCHEMA,
    CHOKEPOINT_MATCH_SCHEMA,
    CLUSTER_TRIAGE_SCHEMA,
    COMPLETENESS_SCHEMA,
    FREE_GENERATION_SCHEMA,
    INVESTMENT_REASONING_SCHEMA,
    LlmChokepointMatcher,
    LlmClusterTriageSelector,
    OpenAICompatibleCompletion,
    TARGET_PROPOSAL_SCHEMA,
    AnthropicCompletion,
    LlmProviderError,
    enforce_chokepoint_match_output,
    enforce_cluster_triage_output,
    enforce_adversarial_output,
    enforce_free_generation_output,
    enforce_investment_reasoning_output,
    enforce_target_candidates,
    schema_allowed_fields,
)
from signal_clustering import SignalCluster
from news_contracts.storage import ContractStore
from news_contracts.validation import validate_target, validate_thesis
from target_generation import LlmTargetProposer, StubPriceLookup, propose_targets
from target_generation.core import _derive_target_id


class StubCompletion:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def __call__(self, *, system, user, schema, max_tokens, thinking):
        self.calls.append(
            {
                "system": system,
                "user": user,
                "schema": schema,
                "max_tokens": max_tokens,
                "thinking": thinking,
            }
        )
        return dict(self.responses[schema["title"]])


def signal():
    return {
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
        "raw_payload": {"source": "rss"},
    }


def free_generation_response():
    return {
        "body": "AI server power module shortages could push urgent orders toward qualified A-share suppliers.",
        "source_signal_ids": ["sig-ai-server-1"],
        "substantive_claims": [
            {
                "text": "AI server backlog expanded and lead times lengthened.",
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
                "description": "Global bottleneck can transmit to A-share power module suppliers.",
                "source_signal_ids": ["sig-ai-server-1"],
            }
        ],
        "falsifiable_expectation": "Within 90 days, qualified suppliers disclose higher AI server orders.",
        "verification_window": {"start": "2026-06-09", "end": "2026-09-07"},
    }


def investment_reasoning_response(**overrides):
    audit = {
        "source_signal_ids": ["sig-ai-server-1"],
        "primary_logic_type": "supply_demand",
        "secondary_logic_types": ["margin_spread_repricing"],
        "evidence_status": "accepted",
        "premise": "AI server backlog and power-module lead times may indicate a supply-demand bottleneck.",
        "upward_validation": [
            {
                "question": "Is the signal grounded in a measurable delta?",
                "answer": "The source reports 25% backlog growth and lead-time extension.",
                "evidence": ["sig-ai-server-1"],
                "status": "supported",
            }
        ],
        "transmission_chain": [
            "AI server backlog -> power module lead-time extension -> qualified supplier order leverage"
        ],
        "downstream_decomposition": [
            "Separate ODMs, power-module suppliers, thermal suppliers, and constrained components."
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


def adversarial_response():
    return {
        "reviewer": "skeptic-reviewer",
        "review_run_id": "review-ai-server-1",
        "strongest_counterargument": "The shortage may already be priced into suppliers and order visibility may be double counted.",
        "hedge_variables": ["order conversion", "price move since signal"],
    }


def candidate_response():
    return {
        "candidates": [
            {
                "id": "target-power-1",
                "symbol": "300001.SZ",
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
                "catalysts": [
                    {
                        "kind": "event",
                        "value": "order_disclosure",
                        "description": "AI server order disclosure or supplier qualification update.",
                    }
                ],
                "exit_triggers": [{"description": "No order conversion before verification window closes."}],
            }
        ]
    }


def test_llm_reasoner_stub_transport_round_trips_through_analyze(tmp_path):
    store = ContractStore(tmp_path / "contracts.db")
    store.add_signal(signal())
    author_transport = StubCompletion(
        {
            "investment_reasoning_audit": investment_reasoning_response(),
            "free_generation": free_generation_response(),
            "completeness_critique": {
                "notes": ["Check second-order thermal and power module suppliers."],
                "candidate_thesis_ids": [],
                "body_unchanged": True,
            },
        }
    )
    reviewer_transport = StubCompletion({"adversarial_falsification": adversarial_response()})
    author = LlmReasoner(
        ReasonerIdentity("author-agent-1", "synthesis-author"),
        transport=author_transport,
    )
    reviewer = LlmReasoner(
        ReasonerIdentity("reviewer-agent-1", "skeptic-reviewer"),
        transport=reviewer_transport,
    )

    result = analyze([signal()], author, reviewer, store, thesis_id="thesis-ai-server-1")

    assert validate_thesis(result.thesis).accepted is True
    assert result.investment_reasoning["primary_logic_type"] == "supply_demand"
    assert result.thesis["investment_reasoning"]["target_search_decision"]["status"] == "allowed"
    assert result.thesis["completeness_critique"]["body_unchanged"] is True
    assert "sig-ai-server-1" in author_transport.calls[0]["user"]
    assert "investment-reasoning-auditor" in author_transport.calls[0]["system"]
    assert author_transport.calls[0]["thinking"] == {"type": "adaptive"}
    assert author_transport.calls[0]["schema"] == INVESTMENT_REASONING_SCHEMA
    assert author_transport.calls[1]["thinking"] == {"type": "adaptive"}
    assert author_transport.calls[2]["thinking"] is None
    assert reviewer_transport.calls[0]["thinking"] == {"type": "adaptive"}


def test_llm_reasoner_investment_reasoning_role_enforces_audit():
    completion = StubCompletion({"investment_reasoning_audit": investment_reasoning_response()})
    reasoner = LlmReasoner(ReasonerIdentity("author-agent-1", "synthesis-author"), transport=completion)

    audit = reasoner.reason("investment_reasoning", {"signals": [signal()], "source_signal_ids": ["sig-ai-server-1"]})

    assert audit["primary_logic_type"] == "supply_demand"
    assert completion.calls[0]["schema"] == INVESTMENT_REASONING_SCHEMA
    assert "primary_logic_type" in completion.calls[0]["user"]


def test_investment_reasoning_output_rejects_hallucinated_source_id():
    with pytest.raises(LlmProviderError, match="unknown source_signal_ids"):
        enforce_investment_reasoning_output(
            investment_reasoning_response(source_signal_ids=["sig-made-up"]),
            {"sig-ai-server-1"},
        )


def test_investment_reasoning_output_rejects_invalid_target_gate():
    with pytest.raises(LlmProviderError, match="cannot allow target search"):
        enforce_investment_reasoning_output(
            investment_reasoning_response(
                evidence_status="weak",
                target_search_decision={"status": "allowed", "reason": "try anyway"},
            ),
            {"sig-ai-server-1"},
        )


def test_llm_target_proposer_stub_transport_round_trips_through_target_generation(tmp_path):
    store = ContractStore(tmp_path / "contracts.db")
    thesis = {
        **free_generation_response(),
        "id": "thesis-ai-server-1",
        "status": "confirmed",
        "completeness_critique": {"notes": ["n"], "candidate_thesis_ids": [], "body_unchanged": True},
        "adversarial_falsification": {
            "reviewer": "skeptic-reviewer",
            "review_session": {
                "thesis_author_id": "author-agent-1",
                "author_persona": "synthesis-author",
                "reviewer_instance_id": "reviewer-agent-1",
                "reviewer_persona": "skeptic-reviewer",
                "review_run_id": "review-ai-server-1",
            },
            "strongest_counterargument": adversarial_response()["strongest_counterargument"],
            "hedge_variables": ["order conversion"],
        },
        "track_record": {
            "direction": "bullish",
            "falsifiable_expectation": "Within 90 days, qualified suppliers disclose higher AI server orders.",
            "verification_window": {"start": "2026-06-09", "end": "2026-09-07"},
            "created_at": "2026-06-09T08:00:00Z",
        },
    }
    store.add_thesis(thesis)
    transport = StubCompletion({"target_proposal": candidate_response()})
    proposer = LlmTargetProposer(transport=transport, symbol_universe={"300001.SZ": "Authoritative Power Co"})

    result = propose_targets(thesis, proposer, StubPriceLookup({"300001.SZ": 0.08}), store)

    assert validate_target(result.targets[0], confirmed_thesis_ids={"thesis-ai-server-1"}).accepted is True
    assert result.targets[0]["name"] == "Authoritative Power Co"
    assert "300001.SZ" in transport.calls[0]["user"]
    assert "Authoritative Power Co" in transport.calls[0]["user"]
    assert "0-100" in transport.calls[0]["user"]
    assert "1-10" in transport.calls[0]["user"]
    assert "0-100" in transport.calls[0]["system"]
    assert "target-analyst" in transport.calls[0]["system"]
    assert transport.calls[0]["thinking"] == {"type": "adaptive"}


def test_anthropic_completion_parses_text_json_and_records_usage():
    client = fake_client(stop_reason="end_turn", text=json.dumps({"ok": True}))
    completion = AnthropicCompletion(client=client)

    assert completion(system="s", user="u", schema={"title": "role"}, max_tokens=10, thinking=None) == {"ok": True}
    assert client.messages.kwargs["output_config"]["format"]["type"] == "json_schema"
    assert completion.usage[0].role == "role"
    assert completion.usage[0].input_tokens == 3


def test_anthropic_completion_passes_base_url_to_lazy_client(monkeypatch):
    captured = {}

    class FakeAnthropic:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setitem(sys.modules, "anthropic", SimpleNamespace(Anthropic=FakeAnthropic))
    completion = AnthropicCompletion(base_url="https://anthropic-relay.example/v1")

    completion._get_client()

    assert captured["base_url"] == "https://anthropic-relay.example/v1"
    assert "api_key" in captured


def test_openai_compatible_completion_schema_mode_parses_and_records_usage():
    client = fake_openai_client(finish_reason="stop", content=json.dumps({"ok": True}))
    completion = OpenAICompatibleCompletion(
        model="deepseek-chat",
        base_url="https://compat.example/v1",
        client=client,
    )
    schema = {"title": "role", "type": "object", "properties": {"ok": {"type": "boolean"}}}

    result = completion(system="s", user="u", schema=schema, max_tokens=20, thinking={"type": "adaptive"})

    assert result == {"ok": True}
    assert client.kwargs["model"] == "deepseek-chat"
    assert client.kwargs["messages"] == [{"role": "system", "content": "s"}, {"role": "user", "content": "u"}]
    assert client.kwargs["response_format"] == {
        "type": "json_schema",
        "json_schema": {"name": "role", "schema": schema, "strict": True},
    }
    assert "thinking" not in client.kwargs
    assert completion.usage[0].input_tokens == 11
    assert completion.usage[0].output_tokens == 7


def test_openai_compatible_completion_object_mode_appends_schema_to_user_prompt():
    client = fake_openai_client(finish_reason="stop", content=json.dumps({"ok": True}))
    completion = OpenAICompatibleCompletion(
        model="relay-model",
        base_url="https://relay.example/v1",
        json_mode="object",
        client=client,
    )
    schema = {"title": "object_role", "type": "object", "properties": {"ok": {"type": "boolean"}}}

    result = completion(system="s", user="original prompt", schema=schema, max_tokens=20, thinking=None)

    assert result == {"ok": True}
    assert client.kwargs["response_format"] == {"type": "json_object"}
    user_prompt = client.kwargs["messages"][1]["content"]
    assert "original prompt" in user_prompt
    assert "You MUST respond with a JSON object conforming to this schema" in user_prompt
    assert '"title": "object_role"' in user_prompt
    assert '"ok"' in user_prompt


@pytest.mark.parametrize("finish_reason", ["length", "content_filter"])
def test_openai_compatible_completion_rejects_bad_finish_reasons(finish_reason):
    completion = OpenAICompatibleCompletion(
        model="compat-model",
        base_url="https://compat.example/v1",
        client=fake_openai_client(finish_reason=finish_reason, content=json.dumps({"ok": True})),
    )

    with pytest.raises(LlmProviderError, match=finish_reason):
        completion(system="s", user="u", schema={"title": "role"}, max_tokens=10, thinking=None)


def test_openai_compatible_completion_rejects_bad_json_and_non_object():
    bad_json = OpenAICompatibleCompletion(
        model="compat-model",
        base_url="https://compat.example/v1",
        client=fake_openai_client(finish_reason="stop", content="not-json"),
    )
    with pytest.raises(LlmProviderError, match="invalid JSON"):
        bad_json(system="s", user="u", schema={"title": "role"}, max_tokens=10, thinking=None)

    non_object = OpenAICompatibleCompletion(
        model="compat-model",
        base_url="https://compat.example/v1",
        client=fake_openai_client(finish_reason="stop", content=json.dumps([{"ok": True}])),
    )
    with pytest.raises(LlmProviderError, match="must be an object"):
        non_object(system="s", user="u", schema={"title": "role"}, max_tokens=10, thinking=None)


def test_openai_compatible_completion_lazy_client_without_env(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    completion = OpenAICompatibleCompletion(
        model="compat-model",
        base_url="https://compat.example/v1",
    )

    assert completion._client is None


@pytest.mark.parametrize("stop_reason", ["refusal", "max_tokens"])
def test_anthropic_completion_rejects_bad_stop_reasons(stop_reason):
    completion = AnthropicCompletion(client=fake_client(stop_reason=stop_reason, text=json.dumps({"ok": True})))

    with pytest.raises(LlmProviderError, match=stop_reason):
        completion(system="s", user="u", schema={"title": "role"}, max_tokens=10, thinking=None)


def test_anthropic_completion_rejects_no_text_and_bad_json():
    with pytest.raises(LlmProviderError, match="text block"):
        AnthropicCompletion(client=fake_client(stop_reason="end_turn", content=[]))(
            system="s", user="u", schema={"title": "role"}, max_tokens=10, thinking=None
        )
    with pytest.raises(LlmProviderError, match="invalid JSON"):
        AnthropicCompletion(client=fake_client(stop_reason="end_turn", text="not-json"))(
            system="s", user="u", schema={"title": "role"}, max_tokens=10, thinking=None
        )


def test_provider_rejects_hallucinated_source_ids():
    bad = free_generation_response()
    bad["substantive_claims"][0]["source_signal_ids"] = ["made-up-sig"]

    with pytest.raises(LlmProviderError, match="unknown source_signal_ids"):
        enforce_free_generation_output(bad, {"sig-ai-server-1"})


def test_cluster_triage_selector_uses_prompt_schema_and_enforces_cluster_ids():
    transport = StubCompletion(
        {
            "cluster_triage": {
                "selected": [{"cluster_id": "cluster-002", "reason": "电力瓶颈具备A股传导价值。"}]
            }
        }
    )
    selector = LlmClusterTriageSelector(transport)
    clusters = [
        SignalCluster("cluster-001", [signal()], "singleton"),
        SignalCluster("cluster-002", [{**signal(), "id": "sig-2", "title": "Data center power wall"}], "singleton"),
    ]

    selected = selector.select(clusters, top_k=1, total_clusters=2, candidate_limit=200)

    assert [(item.cluster_id, item.reason) for item in selected] == [
        ("cluster-002", "电力瓶颈具备A股传导价值。")
    ]
    assert transport.calls[0]["schema"] == CLUSTER_TRIAGE_SCHEMA
    assert transport.calls[0]["thinking"] is None
    assert "AI ecosystem" in transport.calls[0]["system"]
    assert "简体中文" in transport.calls[0]["system"]
    assert "cluster-002" in transport.calls[0]["user"]
    assert "no keyword prefilter" in transport.calls[0]["user"]


def test_cluster_triage_enforcement_rejects_unknown_cluster_and_empty_reason():
    with pytest.raises(LlmProviderError, match="unknown cluster_id"):
        enforce_cluster_triage_output(
            {"selected": [{"cluster_id": "cluster-made-up", "reason": "看起来重要"}]},
            {"cluster-001"},
        )

    with pytest.raises(LlmProviderError, match="reason"):
        enforce_cluster_triage_output(
            {"selected": [{"cluster_id": "cluster-001", "reason": "   "}]},
            {"cluster-001"},
        )


def test_chokepoint_matcher_uses_prompt_schema_and_enforces_node_names():
    transport = StubCompletion(
        {
            "chokepoint_match": {
                "matched": [{"node": "服务器电源HVDC", "reason": "论点直接指向AI服务器电源供给约束。"}]
            }
        }
    )
    matcher = LlmChokepointMatcher(transport)
    nodes = [
        {
            "node": "服务器电源HVDC",
            "chokepoint_holder": "global power supply leaders",
            "china_position": "substitute",
            "triggers": ["800V HVDC", "AI服务器电源"],
            "a_share": [{"code": "002851.SZ", "name": "麦格米特"}],
        }
    ]

    matched = matcher.match(
        {"id": "thesis-1", "body": "AI服务器电源供给趋紧。"},
        signals=[signal()],
        nodes=nodes,
    )

    assert [(item.node, item.reason) for item in matched] == [
        ("服务器电源HVDC", "论点直接指向AI服务器电源供给约束。")
    ]
    assert transport.calls[0]["schema"] == CHOKEPOINT_MATCH_SCHEMA
    assert transport.calls[0]["thinking"] is None
    assert "卡脖子匹配器" in transport.calls[0]["system"]
    assert "真实催化剂" in transport.calls[0]["system"]
    assert "服务器电源HVDC" in transport.calls[0]["user"]


def test_chokepoint_match_enforcement_rejects_hallucinated_node_empty_reason_and_bad_shape():
    with pytest.raises(LlmProviderError, match="matched array"):
        enforce_chokepoint_match_output({"matched": "bad"}, {"服务器电源HVDC"})

    with pytest.raises(LlmProviderError, match="unknown node"):
        enforce_chokepoint_match_output(
            {"matched": [{"node": "Google搜索框", "reason": "误中关键词"}]},
            {"服务器电源HVDC"},
        )

    with pytest.raises(LlmProviderError, match="reason"):
        enforce_chokepoint_match_output(
            {"matched": [{"node": "服务器电源HVDC", "reason": "   "}]},
            {"服务器电源HVDC"},
        )


def test_chokepoint_match_enforcement_dedupes_nodes_in_order():
    matched = enforce_chokepoint_match_output(
        {
            "matched": [
                {"node": "服务器电源HVDC", "reason": "第一次命中。"},
                {"node": "服务器电源HVDC", "reason": "重复命中。"},
                {"node": "液冷", "reason": "第二个节点。"},
            ]
        },
        {"服务器电源HVDC", "液冷"},
    )

    assert matched == [
        {"node": "服务器电源HVDC", "reason": "第一次命中。"},
        {"node": "液冷", "reason": "第二个节点。"},
    ]


@pytest.mark.parametrize(
    ("missing_field", "message"),
    [
        ("direction", "direction"),
        ("confidence", "confidence"),
        ("verification_window", "verification_window"),
    ],
)
def test_llm_reasoner_rejects_missing_free_generation_required_fields(tmp_path, missing_field, message):
    store = ContractStore(tmp_path / "contracts.db")
    store.add_signal(signal())
    response = free_generation_response()
    response.pop(missing_field)
    author = LlmReasoner(
        ReasonerIdentity("author-agent-1", "synthesis-author"),
        transport=StubCompletion(
            {
                "investment_reasoning_audit": investment_reasoning_response(),
                "free_generation": response,
                "completeness_critique": {
                    "notes": ["Check second-order thermal and power module suppliers."],
                    "candidate_thesis_ids": [],
                    "body_unchanged": True,
                },
            }
        ),
    )
    reviewer = LlmReasoner(
        ReasonerIdentity("reviewer-agent-1", "skeptic-reviewer"),
        transport=StubCompletion({"adversarial_falsification": adversarial_response()}),
    )

    with pytest.raises(LlmProviderError, match=message):
        analyze([signal()], author, reviewer, store, thesis_id="thesis-degraded")

    assert store.connection.execute("select count(*) as count from theses").fetchone()["count"] == 0


def test_empty_thesis_source_ids_are_not_replaced_with_all_input_ids(tmp_path):
    store = ContractStore(tmp_path / "contracts.db")
    store.add_signal(signal())
    response = free_generation_response()
    response["source_signal_ids"] = []
    response["substantive_claims"] = []
    response["transmission_path"] = []
    author = LlmReasoner(
        ReasonerIdentity("author-agent-1", "synthesis-author"),
        transport=StubCompletion(
            {
                "investment_reasoning_audit": investment_reasoning_response(),
                "free_generation": response,
                "completeness_critique": {
                    "notes": ["No source-backed thesis-level claim yet."],
                    "candidate_thesis_ids": [],
                    "body_unchanged": True,
                },
            }
        ),
    )
    reviewer = LlmReasoner(
        ReasonerIdentity("reviewer-agent-1", "skeptic-reviewer"),
        transport=StubCompletion({"adversarial_falsification": adversarial_response()}),
    )

    result = analyze([signal()], author, reviewer, store, thesis_id="thesis-no-source")
    stored = store.connection.execute("select payload_json from theses where id = ?", ("thesis-no-source",)).fetchone()
    stored_thesis = json.loads(stored["payload_json"])

    assert result.thesis["source_signal_ids"] == []
    assert stored_thesis["source_signal_ids"] == []
    assert stored_thesis["confidence"] == "low"
    assert "no_source" in stored_thesis["uncertainty_tags"]


def test_provider_rejects_symbol_outside_universe_and_score_range():
    bad_symbol = candidate_response()
    bad_symbol["candidates"][0]["symbol"] = "FAKE"
    with pytest.raises(LlmProviderError, match="outside universe"):
        enforce_target_candidates(bad_symbol, {"300001.SZ": "Authoritative Power Co"})

    bad_score = candidate_response()
    bad_score["candidates"][0]["logic_score"]["score"] = 101
    with pytest.raises(LlmProviderError, match="out of range"):
        enforce_target_candidates(bad_score, {"300001.SZ": "Authoritative Power Co"})


def test_provider_stamps_candidate_name_from_universe_and_ignores_model_name():
    response = candidate_response()
    response["candidates"][0]["name"] = "Hallucinated Name"

    candidates = enforce_target_candidates(response, {"300001.SZ": "Authoritative Power Co"})

    assert candidates[0]["name"] == "Authoritative Power Co"


def test_provider_allows_empty_catalysts_for_target_generation_rejection():
    response = candidate_response()
    response["candidates"][0]["catalysts"] = []

    candidates = enforce_target_candidates(response, {"300001.SZ": "Authoritative Power Co"})

    assert candidates[0]["catalysts"] == []


def test_provider_rejects_damaged_catalyst_or_exit_trigger_structure():
    damaged_catalyst = candidate_response()
    damaged_catalyst["candidates"][0]["catalysts"] = [{"kind": "event", "value": "order"}]
    with pytest.raises(LlmProviderError, match="description"):
        enforce_target_candidates(damaged_catalyst, {"300001.SZ": "Authoritative Power Co"})

    damaged_exit = candidate_response()
    damaged_exit["candidates"][0]["exit_triggers"] = [{}]
    with pytest.raises(LlmProviderError, match="description"):
        enforce_target_candidates(damaged_exit, {"300001.SZ": "Authoritative Power Co"})


def test_empty_catalyst_candidate_is_rejected_without_losing_valid_candidate(tmp_path):
    store = ContractStore(tmp_path / "contracts.db")
    thesis = {
        **free_generation_response(),
        "id": "thesis-ai-server-1",
        "status": "confirmed",
        "completeness_critique": {"notes": ["n"], "candidate_thesis_ids": [], "body_unchanged": True},
        "adversarial_falsification": {
            "reviewer": "skeptic-reviewer",
            "review_session": {
                "thesis_author_id": "author-agent-1",
                "author_persona": "synthesis-author",
                "reviewer_instance_id": "reviewer-agent-1",
                "reviewer_persona": "skeptic-reviewer",
                "review_run_id": "review-ai-server-1",
            },
            "strongest_counterargument": adversarial_response()["strongest_counterargument"],
            "hedge_variables": ["order conversion"],
        },
        "track_record": {
            "direction": "bullish",
            "falsifiable_expectation": "Within 90 days, qualified suppliers disclose higher AI server orders.",
            "verification_window": {"start": "2026-06-09", "end": "2026-09-07"},
            "created_at": "2026-06-09T08:00:00Z",
        },
    }
    store.add_thesis(thesis)
    weak = candidate_response()["candidates"][0]
    weak["id"] = "target-empty-catalyst"
    weak["symbol"] = "300002.SZ"
    weak["catalysts"] = []
    valid = candidate_response()["candidates"][0]
    valid["id"] = "target-valid"
    response = {"candidates": [weak, valid]}
    proposer = LlmTargetProposer(
        transport=StubCompletion({"target_proposal": response}),
        symbol_universe={
            "300001.SZ": "Authoritative Power Co",
            "300002.SZ": "Empty Catalyst Co",
        },
    )

    result = propose_targets(
        thesis,
        proposer,
        StubPriceLookup({"300001.SZ": 0.08, "300002.SZ": 0.02}),
        store,
    )

    assert result.target_ids == [_derive_target_id("300001.SZ", "thesis-ai-server-1")]
    assert result.targets[0]["name"] == "Authoritative Power Co"
    assert result.rejected_reasons == ["300002.SZ: missing catalysts"]


def test_llm_target_proposer_without_symbol_universe_fails_before_transport(tmp_path):
    store = ContractStore(tmp_path / "contracts.db")
    thesis = {
        **free_generation_response(),
        "id": "thesis-ai-server-1",
        "status": "confirmed",
        "completeness_critique": {"notes": ["n"], "candidate_thesis_ids": [], "body_unchanged": True},
        "adversarial_falsification": {
            "reviewer": "skeptic-reviewer",
            "review_session": {
                "thesis_author_id": "author-agent-1",
                "author_persona": "synthesis-author",
                "reviewer_instance_id": "reviewer-agent-1",
                "reviewer_persona": "skeptic-reviewer",
                "review_run_id": "review-ai-server-1",
            },
            "strongest_counterargument": adversarial_response()["strongest_counterargument"],
            "hedge_variables": ["order conversion"],
        },
        "track_record": {
            "direction": "bullish",
            "falsifiable_expectation": "Within 90 days, qualified suppliers disclose higher AI server orders.",
            "verification_window": {"start": "2026-06-09", "end": "2026-09-07"},
            "created_at": "2026-06-09T08:00:00Z",
        },
    }
    store.add_thesis(thesis)
    transport = StubCompletion({"target_proposal": candidate_response()})
    proposer = LlmTargetProposer(transport=transport)

    with pytest.raises(LlmProviderError, match="symbol_universe"):
        propose_targets(thesis, proposer, StubPriceLookup({"300001.SZ": 0.08}), store)

    assert transport.calls == []
    assert store.connection.execute("select count(*) as count from targets").fetchone()["count"] == 0


def test_provider_rejects_empty_notes_hedges_and_hollow_counterargument():
    with pytest.raises(LlmProviderError, match="notes"):
        LlmReasoner(ReasonerIdentity("a", "p"), transport=StubCompletion({"completeness_critique": {"notes": [], "candidate_thesis_ids": []}})).reason(
            "completeness_critique", {"body": "x", "signals": [], "source_signal_ids": []}
        )
    with pytest.raises(LlmProviderError, match="hedge"):
        enforce_adversarial_output({"strongest_counterargument": "This is a detailed objection to the thesis.", "hedge_variables": []}, "body")
    with pytest.raises(LlmProviderError, match="hollow"):
        enforce_adversarial_output({"strongest_counterargument": "too short", "hedge_variables": ["x"]}, "body")
    with pytest.raises(LlmProviderError, match="hollow"):
        enforce_adversarial_output(
            {
                "strongest_counterargument": "This thesis could be wrong because things may change and risks exist without any concrete falsifier.",
                "hedge_variables": ["order conversion"],
            },
            "body",
        )


def test_completeness_critique_requires_body_unchanged_true():
    reasoner = LlmReasoner(
        ReasonerIdentity("author-agent-1", "synthesis-author"),
        transport=StubCompletion(
            {
                "completeness_critique": {
                    "notes": ["Check second-order effects."],
                    "candidate_thesis_ids": [],
                    "body_unchanged": False,
                }
            }
        ),
    )

    with pytest.raises(LlmProviderError, match="body_unchanged"):
        reasoner.reason("completeness_critique", {"body": "x", "signals": [], "source_signal_ids": []})


def test_schema_drift_guard_extras_are_only_expected_orchestration_locals():
    extras = schema_allowed_fields()
    assert extras["free_generation"] == set()
    assert extras["completeness_critique"] == set()
    assert extras["adversarial_falsification"] == set()
    assert extras["target_proposal"] == set()
    assert extras["cluster_triage"] == set()
    assert extras["investment_reasoning"] == set()


def test_output_schemas_use_additional_properties_false():
    assert FREE_GENERATION_SCHEMA["additionalProperties"] is False
    assert TARGET_PROPOSAL_SCHEMA["additionalProperties"] is False
    assert INVESTMENT_REASONING_SCHEMA["additionalProperties"] is False
    assert TARGET_PROPOSAL_SCHEMA["properties"]["candidates"]["items"]["additionalProperties"] is False
    assert CLUSTER_TRIAGE_SCHEMA["additionalProperties"] is False
    assert CLUSTER_TRIAGE_SCHEMA["properties"]["selected"]["items"]["additionalProperties"] is False
    assert "name" not in TARGET_PROPOSAL_SCHEMA["properties"]["candidates"]["items"]["properties"]
    assert "name" not in TARGET_PROPOSAL_SCHEMA["properties"]["candidates"]["items"]["required"]


def test_output_schemas_require_every_declared_property_recursively():
    for schema in (
        FREE_GENERATION_SCHEMA,
        COMPLETENESS_SCHEMA,
        ADVERSARIAL_SCHEMA,
        TARGET_PROPOSAL_SCHEMA,
        CLUSTER_TRIAGE_SCHEMA,
        INVESTMENT_REASONING_SCHEMA,
    ):
        assert_all_object_properties_required(schema)


def test_key_safety_and_lazy_client(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    completion = AnthropicCompletion()
    LlmReasoner(ReasonerIdentity("author-agent-1", "synthesis-author"), transport=completion)
    LlmTargetProposer(transport=completion)

    assert completion._client is None


@pytest.mark.skipif(
    not (os.getenv("ANTHROPIC_API_KEY") and os.getenv("RUN_LIVE_LLM")),
    reason="live LLM smoke requires ANTHROPIC_API_KEY and RUN_LIVE_LLM",
)
def test_live_llm_smoke_invariants(tmp_path):
    store = ContractStore(tmp_path / "contracts.db")
    store.add_signal(signal())
    author = LlmReasoner(ReasonerIdentity("live-author", "synthesis-author"))
    reviewer = LlmReasoner(ReasonerIdentity("live-reviewer", "skeptic-reviewer"))
    analysis = analyze([signal()], author, reviewer, store, thesis_id="live-thesis-1")
    assert set(analysis.thesis["source_signal_ids"]).issubset({"sig-ai-server-1"})
    assert validate_thesis(analysis.thesis).accepted is True


def fake_client(stop_reason: str, text: str | None = None, content=None):
    if content is None:
        content = [SimpleNamespace(type="text", text=text)]
    response = SimpleNamespace(
        stop_reason=stop_reason,
        content=content,
        usage=SimpleNamespace(input_tokens=3, output_tokens=5),
    )
    messages = SimpleNamespace()

    def create(**kwargs):
        messages.kwargs = kwargs
        return response

    messages.create = create
    return SimpleNamespace(messages=messages)


def fake_openai_client(finish_reason: str, content: str):
    response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                finish_reason=finish_reason,
                message=SimpleNamespace(content=content),
            )
        ],
        usage=SimpleNamespace(prompt_tokens=11, completion_tokens=7),
    )

    class FakeCompletions:
        def __init__(self):
            self.kwargs = None

        def create(self, **kwargs):
            self.kwargs = kwargs
            return response

    class FakeClient:
        def __init__(self):
            completions = FakeCompletions()
            self.chat = SimpleNamespace(completions=completions)
            self._completions = completions

        @property
        def kwargs(self):
            return self._completions.kwargs

    return FakeClient()


def assert_all_object_properties_required(schema):
    if schema.get("type") == "object":
        properties = schema.get("properties", {})
        assert set(schema.get("required", [])) == set(properties)
        assert schema.get("additionalProperties") is False
        for subschema in properties.values():
            assert_all_object_properties_required(subschema)
    if schema.get("type") == "array":
        assert_all_object_properties_required(schema["items"])
    if isinstance(schema.get("type"), list) and "array" in schema["type"]:
        assert_all_object_properties_required(schema["items"])
