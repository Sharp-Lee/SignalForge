import json

from analysis_orchestration import ReasonerIdentity, StubReasoner
from news_contracts.storage import ContractStore
from pipeline_orchestration.core import _signal_score
from pipeline_orchestration import run_pipeline
from signal_clustering import SignalCluster
from source_ingestion.adapters.rss import RssAtomAdapter
from source_ingestion.core import FixtureFetcher
from target_generation import StubPriceLookup, StubTargetProposer


def rss_adapter_with_signal(signal_id: str = "sig-ai-server-1"):
    return RssAtomAdapter(
        source_id="rss:semis",
        source_name="Global Semis RSS",
        fetcher=FixtureFetcher(
            [
                {
                    "id": signal_id,
                    "title": "AI server backlog expands 25% as power modules tighten",
                    "link": "https://example.com/ai-server-supply",
                    "published_at": "2026-06-09T08:00:00Z",
                    "summary": "Supplier checks show AI server backlog expanded 25% and power module lead times moved from 6 to 14 weeks.",
                }
            ],
            next_cursor="rss-cursor-1",
        ),
    )


def test_signal_score_prioritizes_energy_infrastructure_terms():
    score = _signal_score(
        {
            "title": "Data center utility signs 300 megawatt grid upgrade",
            "body": "AI data center load requires power grid equipment, battery storage, and liquid cooling upgrades.",
        }
    )

    assert score >= 5


def test_signal_score_prioritizes_ai_software_adoption_terms():
    score = _signal_score(
        {
            "title": "Enterprise AI agent adoption accelerates",
            "body": "Inference software demand expands as enterprises deploy AI agents across workflows.",
        }
    )

    assert score > 0


def rss_adapter_with_items(items: list[dict]):
    return RssAtomAdapter(
        source_id="rss:multi",
        source_name="Multi RSS",
        fetcher=FixtureFetcher(items, next_cursor="rss-cursor-1"),
    )


def rss_adapter_with_cursor_items(items_by_cursor: dict[str | None, list[dict]], source_id: str = "rss:persistent"):
    class CursorAwareFetcher:
        def __init__(self):
            self.calls: list[str | None] = []

        def __call__(self, cursor: str | None):
            from source_ingestion.core import FetchResult

            self.calls.append(cursor)
            return FetchResult(items=list(items_by_cursor.get(cursor, [])), next_cursor="cursor-after-run")

    return RssAtomAdapter(
        source_id=source_id,
        source_name="Persistent RSS",
        fetcher=CursorAwareFetcher(),
    )


class StaticClusterer:
    def __init__(self, groups: list[list[str]]):
        self.groups = groups
        self.calls: list[list[dict]] = []

    def cluster(self, signals: list[dict]) -> list[SignalCluster]:
        self.calls.append(signals)
        by_id = {signal["id"]: signal for signal in signals}
        return [
            SignalCluster(
                id=f"cluster-{index + 1:03d}",
                signals=[by_id[signal_id] for signal_id in group],
                reason="test",
            )
            for index, group in enumerate(self.groups)
        ]


class StubChokepointMatcher:
    def __init__(self, matches):
        self.matches = matches
        self.calls: list[dict] = []

    def match(self, thesis: dict, *, signals: list[dict], nodes: list[dict]):
        self.calls.append({"thesis": thesis, "signals": signals, "nodes": nodes})
        return list(self.matches)


class FailingChokepointMatcher:
    def match(self, thesis: dict, *, signals: list[dict], nodes: list[dict]):
        raise TimeoutError("matcher timed out")


def investment_reasoning_response(source_ids: list[str]) -> dict:
    return {
        "source_signal_ids": source_ids,
        "primary_logic_type": "supply_demand",
        "secondary_logic_types": [],
        "evidence_status": "accepted",
        "premise": "Selected signals contain measurable AI ecosystem investment logic.",
        "upward_validation": [
            {
                "question": "Is there a concrete source-backed delta?",
                "answer": "The selected signal includes a measurable demand, capacity, or infrastructure change.",
                "evidence": source_ids[:1],
                "status": "supported",
            }
        ],
        "transmission_chain": ["signal delta -> constrained AI ecosystem layer -> supplier watchlist relevance"],
        "downstream_decomposition": ["Separate upstream demand, bottleneck node, suppliers, and disconfirming signals."],
        "chokepoint_candidates": [{"node": "AI ecosystem bottleneck", "reason": "The signal identifies constrained supply or demand."}],
        "target_search_decision": {"status": "allowed", "reason": "Evidence and downstream decomposition are sufficient."},
        "missing_evidence": ["Supplier-level confirmation"],
        "disconfirming_evidence": ["Demand normalizes"],
        "public_caveat": "这是一条研究观察逻辑，仍需跟踪后续证据。",
    }


class ContextAwareReasoner:
    def __init__(self, identity: ReasonerIdentity, fail_on: set[str] | None = None):
        self.identity = identity
        self.fail_on = fail_on or set()
        self.calls: list[dict] = []

    def reason(self, role: str, context: dict) -> dict:
        self.calls.append({"role": role, "context": context})
        source_ids = list(context.get("source_signal_ids") or [])
        if role == "free_generation" and set(source_ids) & self.fail_on:
            raise ValueError("forced analysis failure")
        if role == "investment_reasoning":
            return investment_reasoning_response(source_ids)
        if role == "free_generation":
            return {
                "body": f"Cluster thesis for {','.join(source_ids)}.",
                "source_signal_ids": source_ids,
                "substantive_claims": [
                    {
                        "text": f"Claim for {source_ids[0]}",
                        "source_signal_ids": [source_ids[0]],
                    }
                ],
                "direction": "bullish",
                "confidence": "medium",
                "uncertainty_tags": [],
                "origin_market": "global",
                "target_market": "CN-A",
                "transmission_path": [
                    {
                        "description": f"Transmission from {source_ids[0]}",
                        "source_signal_ids": [source_ids[0]],
                    }
                ],
                "falsifiable_expectation": "Qualified suppliers disclose related orders within 90 days.",
                "verification_window": {"start": "2026-06-09", "end": "2026-09-07"},
            }
        if role == "completeness_critique":
            return {
                "notes": ["No missing second-order impact in this test."],
                "candidate_thesis_ids": [],
                "body_unchanged": True,
            }
        return {
            "reviewer": "skeptic-reviewer",
            "review_run_id": f"review-{source_ids[0] if source_ids else 'none'}",
            "strongest_counterargument": "The signal may already be priced in.",
            "hedge_variables": ["order conversion"],
        }


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
            "investment_reasoning": investment_reasoning_response(["sig-ai-server-1"]),
            "free_generation": free_generation,
            "completeness_critique": {
                "notes": ["Check whether ODMs, power modules, or thermal suppliers capture the bottleneck first."],
                "candidate_thesis_ids": [],
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


def raw_item(signal_id: str, title: str, summary: str) -> dict:
    return {
        "id": signal_id,
        "title": title,
        "link": f"https://example.com/{signal_id}",
        "published_at": f"2026-06-09T08:0{signal_id[-1]}:00Z",
        "summary": summary,
    }


def persistent_pipeline_store_counts(store: ContractStore) -> dict[str, int]:
    return {
        "signals": store.connection.execute("select count(*) as count from signals").fetchone()["count"],
        "theses": store.connection.execute("select count(*) as count from theses").fetchone()["count"],
        "targets": store.connection.execute("select count(*) as count from targets").fetchone()["count"],
        "track_record": store.connection.execute("select count(*) as count from track_record").fetchone()["count"],
    }


def test_pipeline_runs_end_to_end_from_signal_to_watchlist_target(tmp_path):
    store = ContractStore(tmp_path / "contracts.db")

    result = run_pipeline(
        adapters=[rss_adapter_with_signal()],
        author_reasoner=author_reasoner(),
        reviewer_reasoner=reviewer_reasoner(),
        proposer=StubTargetProposer([qualified_candidate()]),
        price_lookup=StubPriceLookup({"300001.SZ": 0.08}),
        store=store,
        period="2026-W24",
    )

    assert result.errors == []
    assert result.ingestion.by_source["rss:semis"].accepted == 1
    assert len(result.theses) == 1
    assert len(result.targets) == 1
    assert result.empty_recommendations == []
    assert store.connection.execute("select count(*) as count from signals").fetchone()["count"] == 1
    assert store.connection.execute("select count(*) as count from theses").fetchone()["count"] == 1
    assert store.connection.execute("select count(*) as count from targets").fetchone()["count"] == 1
    assert result.targets[0]["state"] == "watch"


def test_pipeline_chokepoint_match_limits_targets_to_matched_node_symbols(tmp_path):
    store = ContractStore(tmp_path / "contracts.db")
    in_node = qualified_candidate(symbol="002851.SZ", name="Wrong Model Name")
    out_of_node = qualified_candidate(symbol="300001.SZ", name="Legacy Full Universe Candidate")

    result = run_pipeline(
        adapters=[rss_adapter_with_signal()],
        author_reasoner=author_reasoner(),
        reviewer_reasoner=reviewer_reasoner(),
        proposer=StubTargetProposer([out_of_node, in_node]),
        price_lookup=StubPriceLookup({"002851.SZ": 0.08, "300001.SZ": 0.08}),
        store=store,
        period="2026-W24",
        chokepoint_matcher=StubChokepointMatcher(
            [{"node": "服务器电源HVDC", "reason": "AI服务器电源供给约束直接催化HVDC节点。"}]
        ),
    )

    assert result.errors == []
    assert len(result.theses) == 1
    assert result.theses[0]["chokepoint_nodes"] == ["服务器电源HVDC"]
    assert len(result.targets) == 1
    assert result.targets[0]["symbol"] == "002851.SZ"
    assert result.targets[0]["name"] == "麦格米特"
    assert result.targets[0]["chokepoint_node"] == "服务器电源HVDC"
    assert result.targets[0]["chokepoint_holder"]
    assert result.targets[0]["chokepoint_reason"] == "AI服务器电源供给约束直接催化HVDC节点。"
    assert result.chokepoint_matches[result.theses[0]["id"]][0]["node"] == "服务器电源HVDC"
    assert store.connection.execute("select count(*) as count from targets").fetchone()["count"] == 1
    stored = json.loads(store.connection.execute("select payload_json from targets").fetchone()["payload_json"])
    assert stored["chokepoint_node"] == "服务器电源HVDC"
    assert stored["chokepoint_holder"] == result.targets[0]["chokepoint_holder"]


def test_pipeline_chokepoint_no_match_skips_target_generation(tmp_path):
    store = ContractStore(tmp_path / "contracts.db")
    price_lookup = StubPriceLookup({"002851.SZ": 0.08})

    result = run_pipeline(
        adapters=[rss_adapter_with_signal()],
        author_reasoner=author_reasoner(),
        reviewer_reasoner=reviewer_reasoner(),
        proposer=StubTargetProposer([qualified_candidate(symbol="002851.SZ")]),
        price_lookup=price_lookup,
        store=store,
        chokepoint_matcher=StubChokepointMatcher([]),
    )

    assert result.errors == []
    assert len(result.theses) == 1
    assert result.theses[0]["chokepoint_nodes"] == []
    assert result.targets == []
    assert result.no_chokepoint_thesis_ids == [result.theses[0]["id"]]
    assert price_lookup.calls == []
    assert store.connection.execute("select count(*) as count from targets").fetchone()["count"] == 0


def test_pipeline_chokepoint_match_failure_skips_target_generation_fail_closed(tmp_path):
    store = ContractStore(tmp_path / "contracts.db")
    price_lookup = StubPriceLookup({"002851.SZ": 0.08})

    result = run_pipeline(
        adapters=[rss_adapter_with_signal()],
        author_reasoner=author_reasoner(),
        reviewer_reasoner=reviewer_reasoner(),
        proposer=StubTargetProposer([qualified_candidate(symbol="002851.SZ")]),
        price_lookup=price_lookup,
        store=store,
        chokepoint_matcher=FailingChokepointMatcher(),
    )

    assert len(result.theses) == 1
    assert result.targets == []
    assert result.errors[0].stage == "chokepoint-match"
    assert "matcher timed out" in result.errors[0].message
    assert price_lookup.calls == []
    assert store.connection.execute("select count(*) as count from targets").fetchone()["count"] == 0


def test_pipeline_without_chokepoint_matcher_preserves_legacy_target_generation(tmp_path):
    store = ContractStore(tmp_path / "contracts.db")

    result = run_pipeline(
        adapters=[rss_adapter_with_signal()],
        author_reasoner=author_reasoner(),
        reviewer_reasoner=reviewer_reasoner(),
        proposer=StubTargetProposer([qualified_candidate(symbol="300001.SZ")]),
        price_lookup=StubPriceLookup({"300001.SZ": 0.08}),
        store=store,
    )

    assert result.errors == []
    assert len(result.targets) == 1
    assert result.targets[0]["symbol"] == "300001.SZ"
    assert "chokepoint_nodes" not in result.theses[0]


def test_pipeline_records_analysis_failure_without_crashing(tmp_path):
    store = ContractStore(tmp_path / "contracts.db")
    bad_author = StubReasoner(
        ReasonerIdentity(instance_id="author-agent-1", persona="synthesis-author"),
        {
            "investment_reasoning": investment_reasoning_response(["sig-ai-server-1"]),
            "free_generation": {
                "body": "AI server supply pressure could benefit qualified suppliers.",
                "source_signal_ids": ["sig-ai-server-1"],
            },
            "completeness_critique": {},
        },
    )

    result = run_pipeline(
        adapters=[rss_adapter_with_signal()],
        author_reasoner=bad_author,
        reviewer_reasoner=reviewer_reasoner(),
        proposer=StubTargetProposer([qualified_candidate()]),
        price_lookup=StubPriceLookup({"300001.SZ": 0.08}),
        store=store,
    )

    assert result.ingestion.by_source["rss:semis"].accepted == 1
    assert result.theses == []
    assert result.targets == []
    assert result.errors[0].stage == "analysis"
    assert "completeness critique" in result.errors[0].message
    assert store.connection.execute("select count(*) as count from theses").fetchone()["count"] == 0


def test_pipeline_records_target_generation_failure_without_losing_thesis(tmp_path):
    store = ContractStore(tmp_path / "contracts.db")
    malformed_candidate = qualified_candidate(id="target-bad-1")
    malformed_candidate.pop("name")

    result = run_pipeline(
        adapters=[rss_adapter_with_signal()],
        author_reasoner=author_reasoner(),
        reviewer_reasoner=reviewer_reasoner(),
        proposer=StubTargetProposer([malformed_candidate]),
        price_lookup=StubPriceLookup({"300001.SZ": 0.08}),
        store=store,
    )

    assert len(result.theses) == 1
    assert result.targets == []
    assert result.errors[0].stage == "target-generation"
    assert "candidate requires name" in result.errors[0].message
    assert store.connection.execute("select count(*) as count from theses").fetchone()["count"] == 1
    assert store.connection.execute("select count(*) as count from targets").fetchone()["count"] == 0


def test_pipeline_propagates_empty_recommendation(tmp_path):
    store = ContractStore(tmp_path / "contracts.db")
    ineligible = qualified_candidate(
        id="target-weak-1",
        symbol="300003.SZ",
        eligible=False,
        logic_score={"score": 35, "rationale": "Weak thesis linkage."},
    )

    result = run_pipeline(
        adapters=[rss_adapter_with_signal()],
        author_reasoner=author_reasoner(),
        reviewer_reasoner=reviewer_reasoner(),
        proposer=StubTargetProposer([ineligible]),
        price_lookup=StubPriceLookup({"300003.SZ": 0.01}),
        store=store,
        period="2026-W24",
    )

    assert result.errors == []
    assert len(result.theses) == 1
    assert result.targets == []
    assert result.empty_recommendations == [
        {
            "kind": "empty_recommendation",
            "period": "2026-W24",
            "targets": [],
            "reasons": ["300003.SZ: candidate not eligible"],
        }
    ]
    assert store.connection.execute("select count(*) as count from targets").fetchone()["count"] == 0


def test_pipeline_analyzes_multiple_injected_clusters_into_multiple_theses(tmp_path):
    store = ContractStore(tmp_path / "contracts.db")
    candidate = qualified_candidate()
    candidate.pop("id")

    result = run_pipeline(
        adapters=[
            rss_adapter_with_items(
                [
                    raw_item(
                        "sig-cluster-a",
                        "AI server backlog expands 25%",
                        "AI server backlog expanded 25% and power module lead times moved from 6 to 14 weeks.",
                    ),
                    raw_item(
                        "sig-cluster-b",
                        "HBM3E capacity booked above 80%",
                        "HBM3E capacity is more than 80% booked for 2026 and advanced packaging schedules moved out.",
                    ),
                ]
            )
        ],
        author_reasoner=ContextAwareReasoner(ReasonerIdentity("author-agent-1", "synthesis-author")),
        reviewer_reasoner=ContextAwareReasoner(ReasonerIdentity("reviewer-agent-1", "skeptic-reviewer")),
        proposer=StubTargetProposer([candidate]),
        price_lookup=StubPriceLookup({"300001.SZ": 0.08}),
        store=store,
        period="2026-W24",
        clusterer=StaticClusterer([["sig-cluster-a"], ["sig-cluster-b"]]),
    )

    assert result.errors == []
    assert len(result.theses) == 2
    assert len(result.targets) == 2
    assert store.connection.execute("select count(*) as count from theses").fetchone()["count"] == 2
    assert store.connection.execute("select count(*) as count from targets").fetchone()["count"] == 2
    assert [thesis["source_signal_ids"] for thesis in result.theses] == [
        ["sig-cluster-a"],
        ["sig-cluster-b"],
    ]


def test_pipeline_isolates_analysis_failure_per_cluster(tmp_path):
    store = ContractStore(tmp_path / "contracts.db")
    candidate = qualified_candidate()
    candidate.pop("id")

    result = run_pipeline(
        adapters=[
            rss_adapter_with_items(
                [
                    raw_item(
                        "sig-good-1",
                        "AI server backlog expands 25%",
                        "AI server backlog expanded 25% and power module lead times moved from 6 to 14 weeks.",
                    ),
                    raw_item(
                        "sig-bad-2",
                        "Liquid cooling project raises rack power target",
                        "A European data center liquid cooling project targets 120 kW per rack in 2026.",
                    ),
                    raw_item(
                        "sig-good-3",
                        "HBM3E capacity booked above 80%",
                        "HBM3E capacity is more than 80% booked for 2026 and packaging schedules moved out.",
                    ),
                ]
            )
        ],
        author_reasoner=ContextAwareReasoner(
            ReasonerIdentity("author-agent-1", "synthesis-author"),
            fail_on={"sig-bad-2"},
        ),
        reviewer_reasoner=ContextAwareReasoner(ReasonerIdentity("reviewer-agent-1", "skeptic-reviewer")),
        proposer=StubTargetProposer([candidate]),
        price_lookup=StubPriceLookup({"300001.SZ": 0.08}),
        store=store,
        period="2026-W24",
        clusterer=StaticClusterer([["sig-good-1"], ["sig-bad-2"], ["sig-good-3"]]),
    )

    assert len(result.theses) == 2
    assert len(result.targets) == 2
    assert len(result.errors) == 1
    assert result.errors[0].stage == "analysis"
    assert result.errors[0].unit == "cluster-002"
    assert "forced analysis failure" in result.errors[0].message
    assert [thesis["source_signal_ids"] for thesis in result.theses] == [
        ["sig-good-1"],
        ["sig-good-3"],
    ]


def test_persistent_store_second_run_without_new_signals_is_idempotent(tmp_path):
    store_path = tmp_path / "persistent.db"
    store = ContractStore(store_path)
    candidate = qualified_candidate()
    candidate.pop("id")

    first = run_pipeline(
        adapters=[
            rss_adapter_with_cursor_items(
                {
                    None: [
                        raw_item(
                            "sig-persist-1",
                            "AI server backlog expands 25%",
                            "AI server backlog expanded 25% and power module lead times moved from 6 to 14 weeks.",
                        )
                    ],
                    "cursor-after-run": [],
                }
            )
        ],
        author_reasoner=ContextAwareReasoner(ReasonerIdentity("author-agent-1", "synthesis-author")),
        reviewer_reasoner=ContextAwareReasoner(ReasonerIdentity("reviewer-agent-1", "skeptic-reviewer")),
        proposer=StubTargetProposer([candidate]),
        price_lookup=StubPriceLookup({"300001.SZ": 0.08}),
        store=store,
        clusterer=StaticClusterer([["sig-persist-1"]]),
    )
    counts_after_first = persistent_pipeline_store_counts(store)

    reopened = ContractStore(store_path)
    second = run_pipeline(
        adapters=[rss_adapter_with_cursor_items({"cursor-after-run": []})],
        author_reasoner=ContextAwareReasoner(ReasonerIdentity("author-agent-1", "synthesis-author")),
        reviewer_reasoner=ContextAwareReasoner(ReasonerIdentity("reviewer-agent-1", "skeptic-reviewer")),
        proposer=StubTargetProposer([candidate]),
        price_lookup=StubPriceLookup({"300001.SZ": 0.08}),
        store=reopened,
        clusterer=StaticClusterer([]),
    )

    assert first.ingestion.by_source["rss:persistent"].accepted == 1
    assert len(first.theses) == 1
    assert second.ingestion.by_source["rss:persistent"].accepted == 0
    assert second.theses == []
    assert persistent_pipeline_store_counts(reopened) == counts_after_first


def test_persistent_store_accumulates_distinct_new_signal_and_track_record(tmp_path):
    store_path = tmp_path / "persistent.db"
    store = ContractStore(store_path)
    candidate = qualified_candidate()
    candidate.pop("id")

    run_pipeline(
        adapters=[
            rss_adapter_with_items(
                [
                    raw_item(
                        "sig-persist-1",
                        "AI server backlog expands 25%",
                        "AI server backlog expanded 25% and power module lead times moved from 6 to 14 weeks.",
                    )
                ]
            )
        ],
        author_reasoner=ContextAwareReasoner(ReasonerIdentity("author-agent-1", "synthesis-author")),
        reviewer_reasoner=ContextAwareReasoner(ReasonerIdentity("reviewer-agent-1", "skeptic-reviewer")),
        proposer=StubTargetProposer([candidate]),
        price_lookup=StubPriceLookup({"300001.SZ": 0.08}),
        store=store,
        clusterer=StaticClusterer([["sig-persist-1"]]),
    )

    reopened = ContractStore(store_path)
    second = run_pipeline(
        adapters=[
            rss_adapter_with_items(
                [
                    raw_item(
                        "sig-persist-2",
                        "HBM3E packaging capacity booked above 80%",
                        "HBM3E capacity is more than 80% booked for 2026 and advanced packaging schedules moved out.",
                    )
                ]
            )
        ],
        author_reasoner=ContextAwareReasoner(ReasonerIdentity("author-agent-1", "synthesis-author")),
        reviewer_reasoner=ContextAwareReasoner(ReasonerIdentity("reviewer-agent-1", "skeptic-reviewer")),
        proposer=StubTargetProposer([candidate]),
        price_lookup=StubPriceLookup({"300001.SZ": 0.08}),
        store=reopened,
        clusterer=StaticClusterer([["sig-persist-2"]]),
    )

    assert second.ingestion.by_source["rss:multi"].accepted == 1
    assert len(second.theses) == 1
    assert persistent_pipeline_store_counts(reopened)["theses"] == 2
    assert persistent_pipeline_store_counts(reopened)["track_record"] == 2


def test_persistent_store_rejects_near_duplicate_across_runs(tmp_path):
    store_path = tmp_path / "persistent.db"
    store = ContractStore(store_path)
    candidate = qualified_candidate()
    candidate.pop("id")

    run_pipeline(
        adapters=[
            rss_adapter_with_items(
                [
                    raw_item(
                        "sig-persist-1",
                        "AI server backlog expands 25%",
                        "AI server backlog expanded 25% and power module lead times moved from 6 to 14 weeks.",
                    )
                ]
            )
        ],
        author_reasoner=ContextAwareReasoner(ReasonerIdentity("author-agent-1", "synthesis-author")),
        reviewer_reasoner=ContextAwareReasoner(ReasonerIdentity("reviewer-agent-1", "skeptic-reviewer")),
        proposer=StubTargetProposer([candidate]),
        price_lookup=StubPriceLookup({"300001.SZ": 0.08}),
        store=store,
        clusterer=StaticClusterer([["sig-persist-1"]]),
    )

    reopened = ContractStore(store_path)
    second = run_pipeline(
        adapters=[
            rss_adapter_with_items(
                [
                    raw_item(
                        "sig-persist-duplicate",
                        "AI server backlog expands 25 percent",
                        "AI server backlog expanded 25 percent and power module lead times moved from six to fourteen weeks.",
                    )
                ]
            )
        ],
        author_reasoner=ContextAwareReasoner(ReasonerIdentity("author-agent-1", "synthesis-author")),
        reviewer_reasoner=ContextAwareReasoner(ReasonerIdentity("reviewer-agent-1", "skeptic-reviewer")),
        proposer=StubTargetProposer([candidate]),
        price_lookup=StubPriceLookup({"300001.SZ": 0.08}),
        store=reopened,
        clusterer=StaticClusterer([]),
    )

    assert second.ingestion.by_source["rss:multi"].accepted == 0
    assert second.ingestion.by_source["rss:multi"].rejected == 1
    assert "near_duplicate" in second.ingestion.by_source["rss:multi"].errors
    assert second.theses == []
    assert persistent_pipeline_store_counts(reopened)["theses"] == 1
