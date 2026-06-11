from __future__ import annotations

from dataclasses import dataclass, field
import json

from analysis_orchestration import analyze
from signal_clustering import DefaultSignalClusterer
from source_ingestion.runner import run_once
from target_generation import propose_targets


@dataclass
class PipelineError:
    stage: str
    unit: str
    message: str


@dataclass
class PipelineResult:
    ingestion: object
    theses: list[dict] = field(default_factory=list)
    targets: list[dict] = field(default_factory=list)
    empty_recommendations: list[dict] = field(default_factory=list)
    errors: list[PipelineError] = field(default_factory=list)


def run_pipeline(
    *,
    adapters,
    author_reasoner,
    reviewer_reasoner,
    proposer,
    price_lookup,
    store,
    period: str = "current",
    clusterer=None,
) -> PipelineResult:
    before_signal_ids = _signal_ids(store)
    ingestion = run_once(store, adapters)
    result = PipelineResult(ingestion=ingestion)

    new_signals = _newly_persisted_signals(store, before_signal_ids)
    if not new_signals:
        return result

    active_clusterer = clusterer or DefaultSignalClusterer()
    clusters = active_clusterer.cluster(new_signals)

    for cluster in clusters:
        try:
            analysis = analyze(cluster.signals, author_reasoner, reviewer_reasoner, store)
        except Exception as exc:
            result.errors.append(PipelineError(stage="analysis", unit=cluster.id, message=str(exc)))
            continue

        result.theses.append(analysis.thesis)

        try:
            target_result = propose_targets(
                analysis.thesis,
                proposer,
                price_lookup,
                store,
                period=period,
            )
        except Exception as exc:
            result.errors.append(PipelineError(stage="target-generation", unit=analysis.thesis_id, message=str(exc)))
            continue

        result.targets.extend(target_result.targets)
        if target_result.empty_recommendation:
            result.empty_recommendations.append(target_result.empty_recommendation)
    return result


def _signal_ids(store) -> set[str]:
    rows = store.connection.execute("select id from signals").fetchall()
    return {row["id"] for row in rows}


def _newly_persisted_signals(store, before_signal_ids: set[str]) -> list[dict]:
    rows = store.connection.execute(
        "select id, payload_json from signals order by published_at asc, id asc"
    ).fetchall()
    return [
        json.loads(row["payload_json"])
        for row in rows
        if row["id"] not in before_signal_ids
    ]
