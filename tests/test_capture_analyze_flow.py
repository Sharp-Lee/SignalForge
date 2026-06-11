from datetime import UTC, datetime

from analysis_orchestration import ReasonerIdentity, StubReasoner
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


class ContextReasoner:
    def __init__(self, identity: ReasonerIdentity, fail=False):
        self.identity = identity
        self.fail = fail
        self.calls: list[dict] = []

    def reason(self, role: str, context: dict) -> dict:
        self.calls.append({"role": role, "context": context})
        source_ids = list(context.get("source_signal_ids") or [])
        if self.fail and role == "free_generation":
            raise ValueError("forced analysis failure")
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


def test_capture_sources_persists_without_analysis(tmp_path):
    store = ContractStore(tmp_path / "contracts.db")

    result = capture_sources(
        store,
        [rss_adapter("rss:capture", [raw_item("sig-1", "HBM capacity sold out", "HBM capacity sold out for 2027.")])],
    )

    assert result.by_source["rss:capture"].accepted == 1
    assert len(pending_signals(store)) == 1
    assert signal_analysis_counts(store) == {"pending": 1, "analyzed": 0, "skipped_stale": 0, "skipped_failed": 0}
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
    assert signal_analysis_counts(reopened) == {"pending": 3, "analyzed": 1, "skipped_stale": 0, "skipped_failed": 0}

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
    assert signal_analysis_counts(reopened) == {"pending": 2, "analyzed": 2, "skipped_stale": 0, "skipped_failed": 0}


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
    assert signal_analysis_counts(store) == {"pending": 0, "analyzed": 0, "skipped_stale": 1, "skipped_failed": 0}


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
    assert signal_analysis_counts(store) == {"pending": 1, "analyzed": 0, "skipped_stale": 0, "skipped_failed": 0}

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
    assert signal_analysis_counts(store) == {"pending": 0, "analyzed": 0, "skipped_stale": 0, "skipped_failed": 1}

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
