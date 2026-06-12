from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
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
    pending_count: int = 0
    cluster_count: int = 0
    selected_cluster_count: int = 0
    triage_mode: str = "keyword"
    triage_candidate_count: int = 0
    triage_reasons: dict[str, str] = field(default_factory=dict)
    triage_error: str | None = None


@dataclass
class _ClusterSelection:
    clusters: list
    mode: str
    candidate_count: int
    reasons: dict[str, str] = field(default_factory=dict)
    error: str | None = None


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
    top_k: int = 5,
    pending_max_age_days: int = 7,
    max_attempts: int = 2,
    triage_selector=None,
    triage_candidate_limit: int = 200,
) -> PipelineResult:
    ingestion = capture_sources(store, adapters)
    result = analyze_pending(
        store,
        author_reasoner=author_reasoner,
        reviewer_reasoner=reviewer_reasoner,
        proposer=proposer,
        price_lookup=price_lookup,
        period=period,
        clusterer=clusterer,
        top_k=top_k,
        pending_max_age_days=pending_max_age_days,
        max_attempts=max_attempts,
        triage_selector=triage_selector,
        triage_candidate_limit=triage_candidate_limit,
    )
    result.ingestion = ingestion
    return result


def capture_sources(store, adapters):
    return run_once(store, adapters)


def analyze_pending(
    store,
    *,
    author_reasoner,
    reviewer_reasoner,
    proposer,
    price_lookup,
    period: str = "current",
    clusterer=None,
    top_k: int = 5,
    pending_max_age_days: int = 7,
    max_attempts: int = 2,
    triage_selector=None,
    triage_candidate_limit: int = 200,
    now: datetime | None = None,
) -> PipelineResult:
    _ensure_signal_analysis_state(store)
    current_time = now or datetime.now(UTC)
    _mark_stale_pending(store, current_time, pending_max_age_days)
    result = PipelineResult(ingestion=None)

    pending = pending_signals(store)
    result.pending_count = len(pending)
    if not pending:
        return result

    active_clusterer = clusterer or DefaultSignalClusterer()
    clusters = active_clusterer.cluster(pending)
    result.cluster_count = len(clusters)
    selection = _select_clusters_for_analysis(
        clusters,
        top_k=top_k,
        triage_selector=triage_selector,
        triage_candidate_limit=triage_candidate_limit,
    )
    selected_clusters = selection.clusters
    result.selected_cluster_count = len(selected_clusters)
    result.triage_mode = selection.mode
    result.triage_candidate_count = selection.candidate_count
    result.triage_reasons = selection.reasons
    result.triage_error = selection.error

    for cluster in selected_clusters:
        triage_reason = result.triage_reasons.get(cluster.id)
        try:
            analysis = analyze(cluster.signals, author_reasoner, reviewer_reasoner, store)
        except Exception as exc:
            result.errors.append(PipelineError(stage="analysis", unit=cluster.id, message=str(exc)))
            _record_analysis_failure(store, cluster.signals, max_attempts, triage_reason=triage_reason)
            continue

        result.theses.append(analysis.thesis)
        _mark_signals_terminal(store, cluster.signals, "analyzed", triage_reason=triage_reason)

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


def pending_signals(store) -> list[dict]:
    _ensure_signal_analysis_state(store)
    rows = store.connection.execute(
        """
        select s.payload_json
        from signals s
        left join signal_analysis_state a on a.signal_id = s.id
        where a.signal_id is null or a.state = 'pending'
        order by s.published_at asc, s.id asc
        """
    ).fetchall()
    return [json.loads(row["payload_json"]) for row in rows]


def signal_analysis_counts(store) -> dict[str, int]:
    _ensure_signal_analysis_state(store)
    pending_count = store.connection.execute(
        """
        select count(*) as count
        from signals s
        left join signal_analysis_state a on a.signal_id = s.id
        where a.signal_id is null or a.state = 'pending'
        """
    ).fetchone()["count"]
    counts = {"pending": pending_count, "analyzed": 0, "skipped_stale": 0, "skipped_failed": 0}
    rows = store.connection.execute(
        """
        select state, count(*) as count
        from signal_analysis_state
        where state in ('analyzed', 'skipped_stale', 'skipped_failed')
        group by state
        """
    ).fetchall()
    for row in rows:
        counts[row["state"]] = row["count"]
    return counts


def _ensure_signal_analysis_state(store) -> None:
    with store.connection:
        store.connection.execute(
            """
            create table if not exists signal_analysis_state (
                signal_id text primary key,
                state text not null,
                attempts integer not null default 0,
                updated_at text not null,
                foreign key (signal_id) references signals(id)
            )
            """
        )
        columns = {
            row["name"]
            for row in store.connection.execute("pragma table_info(signal_analysis_state)").fetchall()
        }
        if "triage_reason" not in columns:
            store.connection.execute("alter table signal_analysis_state add column triage_reason text")


def _mark_stale_pending(store, now: datetime, pending_max_age_days: int) -> None:
    if pending_max_age_days <= 0:
        return
    cutoff = now.astimezone(UTC) - timedelta(days=pending_max_age_days)
    stale = []
    for signal in pending_signals(store):
        published = _parse_datetime(signal.get("source", {}).get("published_at"))
        if published is not None and published < cutoff:
            stale.append(signal)
    if stale:
        _mark_signals_terminal(store, stale, "skipped_stale", now=now)


def _record_analysis_failure(
    store,
    signals: list[dict],
    max_attempts: int,
    triage_reason: str | None = None,
) -> None:
    _ensure_signal_analysis_state(store)
    now = datetime.now(UTC)
    with store.connection:
        for signal in signals:
            signal_id = signal["id"]
            row = store.connection.execute(
                "select attempts from signal_analysis_state where signal_id = ? and state = 'pending'",
                (signal_id,),
            ).fetchone()
            attempts = (row["attempts"] if row else 0) + 1
            state = "skipped_failed" if attempts >= max_attempts else "pending"
            store.connection.execute(
                """
                insert into signal_analysis_state (signal_id, state, attempts, updated_at, triage_reason)
                values (?, ?, ?, ?, ?)
                on conflict(signal_id) do update set
                    state = excluded.state,
                    attempts = excluded.attempts,
                    updated_at = excluded.updated_at,
                    triage_reason = coalesce(excluded.triage_reason, signal_analysis_state.triage_reason)
                """,
                (signal_id, state, attempts, _to_iso(now), triage_reason),
            )


def _mark_signals_terminal(
    store,
    signals: list[dict],
    state: str,
    now: datetime | None = None,
    triage_reason: str | None = None,
) -> None:
    timestamp = _to_iso(now or datetime.now(UTC))
    with store.connection:
        for signal in signals:
            store.connection.execute(
                """
                insert into signal_analysis_state (signal_id, state, attempts, updated_at, triage_reason)
                values (?, ?, coalesce((select attempts from signal_analysis_state where signal_id = ?), 0), ?, ?)
                on conflict(signal_id) do update set
                    state = excluded.state,
                    attempts = excluded.attempts,
                    updated_at = excluded.updated_at,
                    triage_reason = coalesce(excluded.triage_reason, signal_analysis_state.triage_reason)
                """,
                (signal["id"], state, signal["id"], timestamp, triage_reason),
            )


def _select_clusters_for_analysis(
    clusters,
    *,
    top_k: int,
    triage_selector=None,
    triage_candidate_limit: int = 200,
) -> _ClusterSelection:
    if top_k <= 0:
        return _ClusterSelection([], mode="keyword", candidate_count=0)
    if triage_selector is None:
        return _ClusterSelection(
            _select_top_clusters(clusters, top_k),
            mode="keyword",
            candidate_count=0,
        )
    candidate_clusters = _freshest_clusters(clusters, triage_candidate_limit)
    try:
        selected = triage_selector.select(
            candidate_clusters,
            top_k,
            total_clusters=len(clusters),
            candidate_limit=triage_candidate_limit,
        )
    except Exception as exc:  # noqa: BLE001 - fallback is intentional selection safety.
        return _ClusterSelection(
            _select_top_clusters(clusters, top_k),
            mode="fallback_keyword",
            candidate_count=len(candidate_clusters),
            error=str(exc),
        )
    if not selected:
        return _ClusterSelection(
            _select_top_clusters(clusters, top_k),
            mode="fallback_keyword",
            candidate_count=len(candidate_clusters),
            error="empty triage selection",
        )

    by_id = {cluster.id: cluster for cluster in candidate_clusters}
    chosen = []
    reasons = {}
    for item in selected:
        cluster_id = item.cluster_id if hasattr(item, "cluster_id") else item.get("cluster_id")
        reason = item.reason if hasattr(item, "reason") else item.get("reason")
        cluster = by_id.get(cluster_id)
        if cluster is None:
            return _ClusterSelection(
                _select_top_clusters(clusters, top_k),
                mode="fallback_keyword",
                candidate_count=len(candidate_clusters),
                error=f"triage selected unknown cluster_id: {cluster_id}",
            )
        if not isinstance(reason, str) or not reason.strip():
            return _ClusterSelection(
                _select_top_clusters(clusters, top_k),
                mode="fallback_keyword",
                candidate_count=len(candidate_clusters),
                error=f"triage selected {cluster_id} without reason",
            )
        if cluster_id not in reasons:
            chosen.append(cluster)
            reasons[cluster_id] = reason.strip()
        if len(chosen) >= top_k:
            break
    if not chosen:
        return _ClusterSelection(
            _select_top_clusters(clusters, top_k),
            mode="fallback_keyword",
            candidate_count=len(candidate_clusters),
            error="empty triage selection",
        )
    return _ClusterSelection(chosen, mode="llm_triage", candidate_count=len(candidate_clusters), reasons=reasons)


def _freshest_clusters(clusters, limit: int):
    if limit <= 0:
        return []
    return sorted(clusters, key=lambda cluster: (_cluster_newest_datetime(cluster), cluster.id), reverse=True)[:limit]


def _cluster_newest_datetime(cluster) -> datetime:
    values = [_parse_datetime((signal.get("source") or {}).get("published_at")) for signal in cluster.signals]
    valid = [value for value in values if value is not None]
    return max(valid) if valid else datetime.min.replace(tzinfo=UTC)


def _select_top_clusters(clusters, top_k: int):
    if top_k <= 0:
        return []
    return sorted(clusters, key=lambda cluster: (-_cluster_score(cluster), cluster.id))[:top_k]


def _cluster_score(cluster) -> int:
    if not cluster.signals:
        return 0
    return max(_signal_score(signal) for signal in cluster.signals) + min(len(cluster.signals) - 1, 2)


def _signal_score(signal: dict) -> int:
    text = f"{signal.get('title', '')}\n{signal.get('body', '')}".lower()
    score = 0
    if any(ch.isdigit() for ch in text):
        score += 3
    if any(
        term in text
        for term in (
            "%",
            "week",
            "month",
            "capacity",
            "order",
            "lead time",
            "sold out",
            "megawatt",
            "gigawatt",
        )
    ):
        score += 3
    if any(
        term in text
        for term in (
            "hbm",
            "memory",
            "optical",
            "module",
            "power",
            "pcb",
            "server",
            "ai cluster",
            "data center",
            "datacenter",
            "grid",
            "power grid",
            "energy",
            "electric",
            "utility",
            "solar",
            "storage",
            "battery",
            "cooling",
            "liquid cooling",
            "inference",
            "agent",
            "enterprise ai",
            "ai software",
        )
    ):
        score += 2
    if _is_generic(text):
        score -= 3
    return score


def _is_generic(text: str) -> bool:
    generic_terms = ("ai", "compute", "robot", "semiconductor", "technology")
    specific_terms = (
        "agent",
        "inference",
        "enterprise ai",
        "ai software",
        "data center",
        "datacenter",
        "grid",
        "utility",
        "cooling",
        "storage",
        "battery",
        "hbm",
        "optical",
        "power",
    )
    return (
        any(term in text for term in generic_terms)
        and not any(ch.isdigit() for ch in text)
        and not any(term in text for term in specific_terms)
    )


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        if value.endswith("Z"):
            return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
        return datetime.fromisoformat(value).astimezone(UTC)
    except ValueError:
        return None


def _to_iso(value: datetime) -> str:
    return value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
