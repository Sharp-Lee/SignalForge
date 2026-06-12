from datetime import UTC, datetime

from analysis_orchestration import ReasonerIdentity, StubReasoner
from llm_provider import TriageSelection
from news_contracts.storage import ContractStore
from pipeline_orchestration import (
    analyze_pending,
    capture_sources,
    pending_signals,
    signal_analysis_counts,
)
from signal_clustering import SignalCluster
from source_ingestion.adapters.rss import RssAtomAdapter
from source_ingestion.core import FixtureFetcher
from target_generation import StubPriceLookup, StubTargetProposer


def rss_adapter(source_id: str, items: list[dict]):
    return RssAtomAdapter(
        source_id=source_id,
        source_name=source_id,
        fetcher=FixtureFetcher(items, next_cursor=f"{source_id}:cursor"),
    )


def raw_item(signal_id: str, title: str, summary: str, published_at: str = "2026-06-12T08:00:00Z"):
    return {
        "id": signal_id,
        "title": title,
        "link": f"https://example.com/{signal_id}",
        "published_at": published_at,
        "summary": summary,
    }


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
            if all(signal_id in by_id for signal_id in group)
        ]


class StubTriageSelector:
    def __init__(self, selections=None, error: Exception | None = None):
        self.selections = selections if selections is not None else []
        self.error = error
        self.calls = []

    def select(self, clusters, top_k, **kwargs):
        self.calls.append({"cluster_ids": [cluster.id for cluster in clusters], "top_k": top_k, "kwargs": kwargs})
        if self.error is not None:
            raise self.error
        return list(self.selections)


def investment_reasoning_response(source_ids: list[str], **overrides) -> dict:
    audit = {
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
    audit.update(overrides)
    return audit


class ContextReasoner:
    def __init__(self, identity: ReasonerIdentity, fail=False, evidence_status: str = "accepted"):
        self.identity = identity
        self.fail = fail
        self.evidence_status = evidence_status
        self.calls: list[dict] = []

    def reason(self, role: str, context: dict) -> dict:
        self.calls.append({"role": role, "context": context})
        source_ids = list(context.get("source_signal_ids") or [])
        if self.fail and role == "free_generation":
            raise ValueError("forced analysis failure")
        if role == "investment_reasoning":
            if self.evidence_status == "accepted":
                return investment_reasoning_response(source_ids)
            target_status = "not_ready" if self.evidence_status == "weak" else "blocked"
            return investment_reasoning_response(
                source_ids,
                evidence_status=self.evidence_status,
                target_search_decision={"status": target_status, "reason": "Insufficient investment logic."},
                transmission_chain=[],
                downstream_decomposition=[],
            )
        if role == "free_generation":
            return {
                "body": f"Cluster thesis for {','.join(source_ids)}.",
                "source_signal_ids": source_ids,
                "substantive_claims": [
                    {"text": f"Claim for {source_ids[0]}", "source_signal_ids": [source_ids[0]]}
                ],
                "direction": "bullish",
                "confidence": "medium",
                "uncertainty_tags": [],
                "origin_market": "global",
                "target_market": "CN-A",
                "transmission_path": [
                    {"description": f"Transmission from {source_ids[0]}", "source_signal_ids": [source_ids[0]]}
                ],
                "falsifiable_expectation": "Qualified suppliers disclose related orders within 90 days.",
                "verification_window": {"start": "2026-06-12", "end": "2026-09-10"},
            }
        if role == "completeness_critique":
            return {"notes": ["No missing second-order impact."], "candidate_thesis_ids": [], "body_unchanged": True}
        return {
            "reviewer": "skeptic-reviewer",
            "review_run_id": f"review-{source_ids[0]}",
            "strongest_counterargument": "The signal may already be priced in.",
            "hedge_variables": ["order conversion"],
        }


def author(fail=False):
    return ContextReasoner(ReasonerIdentity(instance_id="author-agent-1", persona="synthesis-author"), fail=fail)


def non_actionable_author(evidence_status: str):
    return ContextReasoner(
        ReasonerIdentity(instance_id="author-agent-1", persona="synthesis-author"),
        evidence_status=evidence_status,
    )


def reviewer():
    return ContextReasoner(ReasonerIdentity(instance_id="reviewer-agent-1", persona="skeptic-reviewer"))


def candidate(symbol="300001.SZ"):
    return {
        "id": f"candidate-{symbol}",
        "symbol": symbol,
        "name": "Power Module Supplier",
        "target_market": "CN-A",
        "eligible": True,
        "logic_score": {"score": 82, "rationale": "Strong link."},
        "buy_point": {"status": "neutral", "rationale": "Watch valuation."},
        "catalysts": [{"description": "Order disclosure."}],
        "exit_triggers": [{"description": "No order conversion."}],
    }


def expected_counts(
    *,
    pending: int = 0,
    analyzed: int = 0,
    skipped_stale: int = 0,
    skipped_failed: int = 0,
    skipped_weak_logic: int = 0,
    skipped_rejected_logic: int = 0,
) -> dict[str, int]:
    return {
        "pending": pending,
        "analyzed": analyzed,
        "skipped_stale": skipped_stale,
        "skipped_failed": skipped_failed,
        "skipped_weak_logic": skipped_weak_logic,
        "skipped_rejected_logic": skipped_rejected_logic,
    }


def test_capture_sources_persists_without_analysis(tmp_path):
    store = ContractStore(tmp_path / "contracts.db")

    result = capture_sources(
        store,
        [rss_adapter("rss:capture", [raw_item("sig-1", "HBM capacity sold out", "HBM capacity sold out for 2027.")])],
    )

    assert result.by_source["rss:capture"].accepted == 1
    assert len(pending_signals(store)) == 1
    assert signal_analysis_counts(store) == expected_counts(pending=1)
    assert store.connection.execute("select count(*) as count from theses").fetchone()["count"] == 0


def test_analyze_pending_survives_reopen_and_enforces_top_k(tmp_path):
    db_path = tmp_path / "contracts.db"
    store = ContractStore(db_path)
    capture_sources(
        store,
        [
            rss_adapter(
                "rss:capture-1",
                [
                    raw_item("sig-1", "HBM supplier says 2027 capacity sold out", "Capacity sold out with 52 week lead time."),
                    raw_item("sig-2", "Software dashboard refresh", "Minor UI update for enterprise software."),
                ],
            ),
            rss_adapter(
                "rss:capture-2",
                [
                    raw_item("sig-3", "Optical module lead times extend to 20 weeks", "AI cluster demand extends lead times."),
                    raw_item("sig-4", "Consumer gadget color update", "New color option announced."),
                ],
            ),
        ],
    )
    store.connection.close()

    reopened = ContractStore(db_path)
    assert len(pending_signals(reopened)) == 4

    result = analyze_pending(
        reopened,
        author_reasoner=author(),
        reviewer_reasoner=reviewer(),
        proposer=StubTargetProposer([candidate()]),
        price_lookup=StubPriceLookup({"300001.SZ": 0.02}),
        clusterer=StaticClusterer([["sig-1"], ["sig-2"], ["sig-3"], ["sig-4"]]),
        top_k=1,
        now=datetime(2026, 6, 12, tzinfo=UTC),
    )

    assert result.errors == []
    assert len(result.theses) == 1
    assert result.theses[0]["source_signal_ids"] == ["sig-1"]
    assert result.pending_count == 4
    assert result.cluster_count == 4
    assert result.selected_cluster_count == 1
    assert signal_analysis_counts(reopened) == expected_counts(pending=3, analyzed=1)

    second = analyze_pending(
        reopened,
        author_reasoner=author(),
        reviewer_reasoner=reviewer(),
        proposer=StubTargetProposer([candidate("300002.SZ")]),
        price_lookup=StubPriceLookup({"300002.SZ": 0.03}),
        clusterer=StaticClusterer([["sig-1"], ["sig-2"], ["sig-3"], ["sig-4"]]),
        top_k=1,
        now=datetime(2026, 6, 12, tzinfo=UTC),
    )

    assert second.theses[0]["source_signal_ids"] == ["sig-3"]
    assert signal_analysis_counts(reopened) == expected_counts(pending=2, analyzed=2)


def test_analyze_pending_uses_llm_triage_selection_and_persists_reason(tmp_path):
    store = ContractStore(tmp_path / "contracts.db")
    capture_sources(
        store,
        [
            rss_adapter(
                "rss:triage",
                [
                    raw_item("sig-low", "Minor software dashboard refresh", "Minor UI update.", "2026-06-12T08:00:00Z"),
                    raw_item(
                        "sig-power",
                        "Data center power wall by 2030",
                        "Report warns AI data center growth may run into a power wall by 2030.",
                        "2026-06-12T09:00:00Z",
                    ),
                ],
            )
        ],
    )
    triage = StubTriageSelector(
        [TriageSelection("cluster-002", "电力瓶颈具备A股电网设备和储能传导价值。")]
    )

    result = analyze_pending(
        store,
        author_reasoner=author(),
        reviewer_reasoner=reviewer(),
        proposer=StubTargetProposer([candidate()]),
        price_lookup=StubPriceLookup({"300001.SZ": 0.02}),
        clusterer=StaticClusterer([["sig-low"], ["sig-power"]]),
        top_k=1,
        triage_selector=triage,
        now=datetime(2026, 6, 12, tzinfo=UTC),
    )

    assert result.triage_mode == "llm_triage"
    assert result.triage_candidate_count == 2
    assert result.triage_reasons == {"cluster-002": "电力瓶颈具备A股电网设备和储能传导价值。"}
    assert result.theses[0]["source_signal_ids"] == ["sig-power"]
    assert signal_analysis_counts(store) == expected_counts(pending=1, analyzed=1)
    row = store.connection.execute(
        "select triage_reason from signal_analysis_state where signal_id = ?",
        ("sig-power",),
    ).fetchone()
    assert row["triage_reason"] == "电力瓶颈具备A股电网设备和储能传导价值。"


def test_analyze_pending_triage_failure_empty_or_unknown_falls_back_to_keyword_top_k(tmp_path):
    for triage_selector in [
        StubTriageSelector(error=RuntimeError("triage unavailable")),
        StubTriageSelector([]),
        StubTriageSelector([{"cluster_id": "cluster-made-up", "reason": "bad"}]),
    ]:
        store = ContractStore(tmp_path / f"contracts-{len(triage_selector.calls)}-{id(triage_selector)}.db")
        capture_sources(
            store,
            [
                rss_adapter(
                    "rss:fallback",
                    [
                        raw_item(
                            "sig-keyword",
                            "HBM capacity sold out for 2027",
                            "HBM capacity sold out with 52 week lead time.",
                            "2026-06-12T08:00:00Z",
                        ),
                        raw_item("sig-noise", "Minor app icon refresh", "A consumer app changed its icon.", "2026-06-12T09:00:00Z"),
                    ],
                )
            ],
        )

        result = analyze_pending(
            store,
            author_reasoner=author(),
            reviewer_reasoner=reviewer(),
            proposer=StubTargetProposer([candidate()]),
            price_lookup=StubPriceLookup({"300001.SZ": 0.02}),
            clusterer=StaticClusterer([["sig-noise"], ["sig-keyword"]]),
            top_k=1,
            triage_selector=triage_selector,
            now=datetime(2026, 6, 12, tzinfo=UTC),
        )

        assert result.triage_mode == "fallback_keyword"
        assert result.theses[0]["source_signal_ids"] == ["sig-keyword"]
        assert result.triage_error


def test_analyze_pending_triage_candidate_limit_uses_newest_clusters(tmp_path):
    store = ContractStore(tmp_path / "contracts.db")
    capture_sources(
        store,
        [
            rss_adapter(
                "rss:freshness",
                [
                    raw_item(
                        "sig-old",
                        "HBM capacity sold out for 2027",
                        "HBM capacity sold out with 52 week lead time.",
                        "2026-06-10T08:00:00Z",
                    ),
                    raw_item("sig-middle", "AI agents enter enterprise workflows", "Enterprise AI agents are deployed.", "2026-06-11T08:00:00Z"),
                    raw_item("sig-new", "Grid upgrade for AI data center", "Utility plans grid upgrade for AI data center load.", "2026-06-12T08:00:00Z"),
                ],
            )
        ],
    )
    triage = StubTriageSelector([TriageSelection("cluster-003", "最新电网升级信号优先。")])

    result = analyze_pending(
        store,
        author_reasoner=author(),
        reviewer_reasoner=reviewer(),
        proposer=StubTargetProposer([candidate()]),
        price_lookup=StubPriceLookup({"300001.SZ": 0.02}),
        clusterer=StaticClusterer([["sig-old"], ["sig-middle"], ["sig-new"]]),
        top_k=1,
        triage_selector=triage,
        triage_candidate_limit=2,
        now=datetime(2026, 6, 12, tzinfo=UTC),
    )

    assert triage.calls[0]["cluster_ids"] == ["cluster-003", "cluster-002"]
    assert triage.calls[0]["kwargs"] == {"total_clusters": 3, "candidate_limit": 2}
    assert result.theses[0]["source_signal_ids"] == ["sig-new"]


def test_analyze_pending_marks_old_signals_skipped_stale(tmp_path):
    store = ContractStore(tmp_path / "contracts.db")
    capture_sources(
        store,
        [
            rss_adapter(
                "rss:old",
                [raw_item("sig-old", "Old capacity shortage", "Old but important signal.", "2026-06-01T08:00:00Z")],
            )
        ],
    )
    test_author = author()

    result = analyze_pending(
        store,
        author_reasoner=test_author,
        reviewer_reasoner=reviewer(),
        proposer=StubTargetProposer([candidate()]),
        price_lookup=StubPriceLookup({"300001.SZ": 0.02}),
        top_k=5,
        pending_max_age_days=7,
        now=datetime(2026, 6, 12, tzinfo=UTC),
    )

    assert result.theses == []
    assert test_author.calls == []
    assert signal_analysis_counts(store) == expected_counts(skipped_stale=1)


def test_analyze_pending_marks_repeated_failures_skipped_failed(tmp_path):
    store = ContractStore(tmp_path / "contracts.db")
    capture_sources(
        store,
        [
            rss_adapter(
                "rss:bad",
                [raw_item("sig-bad", "Bad cluster with 20 week lead time", "This selected cluster fails analysis.")],
            )
        ],
    )
    failing_author = author(fail=True)

    first = analyze_pending(
        store,
        author_reasoner=failing_author,
        reviewer_reasoner=reviewer(),
        proposer=StubTargetProposer([candidate()]),
        price_lookup=StubPriceLookup({"300001.SZ": 0.02}),
        top_k=1,
        max_attempts=2,
        now=datetime(2026, 6, 12, tzinfo=UTC),
    )
    assert len(first.errors) == 1
    assert signal_analysis_counts(store) == expected_counts(pending=1)

    second = analyze_pending(
        store,
        author_reasoner=failing_author,
        reviewer_reasoner=reviewer(),
        proposer=StubTargetProposer([candidate()]),
        price_lookup=StubPriceLookup({"300001.SZ": 0.02}),
        top_k=1,
        max_attempts=2,
        now=datetime(2026, 6, 12, tzinfo=UTC),
    )
    assert len(second.errors) == 1
    assert signal_analysis_counts(store) == expected_counts(skipped_failed=1)

    calls_after_cap = len(failing_author.calls)
    third = analyze_pending(
        store,
        author_reasoner=failing_author,
        reviewer_reasoner=reviewer(),
        proposer=StubTargetProposer([candidate()]),
        price_lookup=StubPriceLookup({"300001.SZ": 0.02}),
        top_k=1,
        max_attempts=2,
        now=datetime(2026, 6, 12, tzinfo=UTC),
    )
    assert third.theses == []
    assert len(failing_author.calls) == calls_after_cap


def test_analyze_pending_marks_weak_and_rejected_reasoning_terminal_without_retry(tmp_path):
    for evidence_status, expected_state in [
        ("weak", "skipped_weak_logic"),
        ("rejected", "skipped_rejected_logic"),
    ]:
        store = ContractStore(tmp_path / f"{evidence_status}.db")
        capture_sources(
            store,
            [
                rss_adapter(
                    f"rss:{evidence_status}",
                    [raw_item(f"sig-{evidence_status}", "Generic AI commentary", "No measurable investment delta.")],
                )
            ],
        )
        test_author = non_actionable_author(evidence_status)

        result = analyze_pending(
            store,
            author_reasoner=test_author,
            reviewer_reasoner=reviewer(),
            proposer=StubTargetProposer([candidate()]),
            price_lookup=StubPriceLookup({"300001.SZ": 0.02}),
            top_k=1,
            max_attempts=1,
            now=datetime(2026, 6, 12, tzinfo=UTC),
        )

        assert result.theses == []
        assert result.targets == []
        assert result.errors[0].stage == "analysis-skip"
        assert expected_state in signal_analysis_counts(store)
        assert signal_analysis_counts(store)[expected_state] == 1
        assert signal_analysis_counts(store)["skipped_failed"] == 0
        assert [call["role"] for call in test_author.calls] == ["investment_reasoning"]
