from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
import inspect
import json

from analysis_orchestration import AnalysisSkipped, analyze
from market_data.chokepoint_map import curated_nodes
from signal_clustering import DefaultSignalClusterer
from source_ingestion.runner import run_once
from target_generation import LlmTargetProposer, propose_targets


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
    chokepoint_matches: dict[str, list[dict]] = field(default_factory=dict)
    no_chokepoint_thesis_ids: list[str] = field(default_factory=list)


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
    chokepoint_matcher=None,
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
        chokepoint_matcher=chokepoint_matcher,
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
    chokepoint_matcher=None,
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
            analysis = analyze(
                cluster.signals,
                author_reasoner,
                reviewer_reasoner,
                store,
                # Chokepoint gate, when present, is the sole relevance authority:
                # let the reasoning audit annotate without vetoing so matched
                # signals reach the grounded ④ gate.
                enforce_reasoning_gate=chokepoint_matcher is None,
            )
        except AnalysisSkipped as exc:
            result.errors.append(PipelineError(stage="analysis-skip", unit=cluster.id, message=str(exc)))
            state = _analysis_skip_state(exc.evidence_status)
            _mark_signals_terminal(store, cluster.signals, state, triage_reason=triage_reason)
            continue
        except Exception as exc:
            result.errors.append(PipelineError(stage="analysis", unit=cluster.id, message=str(exc)))
            _record_analysis_failure(store, cluster.signals, max_attempts, triage_reason=triage_reason)
            continue

        _mark_signals_terminal(store, cluster.signals, "analyzed", triage_reason=triage_reason)

        target_proposer = proposer
        chokepoint_context = None
        if chokepoint_matcher is not None:
            try:
                chokepoint_context = _match_chokepoints(analysis.thesis, cluster.signals, chokepoint_matcher)
            except Exception as exc:  # noqa: BLE001 - gate is fail-closed by design.
                analysis.thesis["chokepoint_nodes"] = []
                result.theses.append(analysis.thesis)
                result.errors.append(PipelineError(stage="chokepoint-match", unit=analysis.thesis_id, message=str(exc)))
                continue
            if not chokepoint_context["nodes"]:
                analysis.thesis["chokepoint_nodes"] = []
                result.theses.append(analysis.thesis)
                result.no_chokepoint_thesis_ids.append(analysis.thesis_id)
                result.chokepoint_matches[analysis.thesis_id] = []
                continue
            analysis.thesis["chokepoint_nodes"] = [node["node"] for node in chokepoint_context["nodes"]]
            result.chokepoint_matches[analysis.thesis_id] = [
                {
                    "node": node["node"],
                    "reason": chokepoint_context["reasons"].get(node["node"], ""),
                    "chokepoint_holder": node["chokepoint_holder"],
                }
                for node in chokepoint_context["nodes"]
            ]
            target_proposer = _restrict_proposer_to_chokepoint_context(proposer, chokepoint_context)

        result.theses.append(analysis.thesis)

        try:
            target_result = propose_targets(
                analysis.thesis,
                target_proposer,
                price_lookup,
                store,
                period=period,
            )
        except Exception as exc:
            result.errors.append(PipelineError(stage="target-generation", unit=analysis.thesis_id, message=str(exc)))
            continue

        if chokepoint_context is not None:
            _annotate_targets_with_chokepoint_context(target_result.targets, chokepoint_context)
        result.targets.extend(target_result.targets)
        if target_result.empty_recommendation:
            result.empty_recommendations.append(target_result.empty_recommendation)
    return result


def _match_chokepoints(thesis: dict, signals: list[dict], matcher) -> dict:
    nodes = curated_nodes()
    if not nodes:
        return {"nodes": [], "reasons": {}}
    raw_matches = matcher.match(thesis, signals=signals, nodes=nodes)
    by_node = {node["node"]: node for node in nodes}
    matched_nodes = []
    reasons = {}
    for item in raw_matches:
        node_name = item.node if hasattr(item, "node") else item.get("node")
        reason = item.reason if hasattr(item, "reason") else item.get("reason")
        if node_name not in by_node:
            raise ValueError(f"chokepoint matcher selected unknown node: {node_name}")
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError(f"chokepoint matcher selected {node_name} without reason")
        if node_name in reasons:
            continue
        matched_nodes.append(by_node[node_name])
        reasons[node_name] = reason.strip()
    return {"nodes": matched_nodes, "reasons": reasons}


def _restrict_proposer_to_chokepoint_context(proposer, context: dict):
    nodes = context["nodes"]
    symbol_universe = _symbol_universe_from_nodes(nodes, getattr(proposer, "symbol_universe", None))
    if isinstance(proposer, LlmTargetProposer):
        restricted = LlmTargetProposer(
            system_prompt=proposer.system_prompt,
            transport=proposer.transport,
            symbol_universe=symbol_universe,
            max_tokens=proposer.max_tokens,
        )
    else:
        restricted = _SymbolUniverseFilteringProposer(proposer, symbol_universe)
    return _ChokepointContextProposer(restricted, context)


def _symbol_universe_from_nodes(nodes: list[dict], authoritative_universe: dict[str, str] | None = None) -> dict[str, str]:
    universe = dict(authoritative_universe or {})
    scoped: dict[str, str] = {}
    for node in nodes:
        for record in node.get("a_share") or []:
            code = record.get("code")
            if not code or code in scoped:
                continue
            scoped[code] = universe.get(code) or record.get("name") or code
    return scoped


class _SymbolUniverseFilteringProposer:
    def __init__(self, proposer, symbol_universe: dict[str, str]):
        self.proposer = proposer
        self.symbol_universe = symbol_universe

    def propose(self, thesis: dict) -> list[dict]:
        candidates = []
        for candidate in self.proposer.propose(thesis):
            symbol = candidate.get("symbol")
            if symbol not in self.symbol_universe:
                continue
            stamped = dict(candidate)
            stamped["name"] = self.symbol_universe[symbol]
            candidates.append(stamped)
        return candidates


class _ChokepointContextProposer:
    def __init__(self, proposer, context: dict):
        self.proposer = proposer
        self.metadata_by_symbol = _target_metadata_by_symbol(context["nodes"], context["reasons"])

    def propose(self, thesis: dict) -> list[dict]:
        candidates = []
        for candidate in self.proposer.propose(thesis):
            symbol = candidate.get("symbol")
            metadata = self.metadata_by_symbol.get(symbol)
            if not metadata:
                candidates.append(candidate)
                continue
            stamped = dict(candidate)
            stamped.update(metadata)
            candidates.append(stamped)
        return candidates


def _target_metadata_by_symbol(nodes: list[dict], reasons: dict[str, str]) -> dict[str, dict[str, str]]:
    metadata = {}
    for node in nodes:
        for record in node.get("a_share") or []:
            symbol = record.get("code")
            if symbol and symbol not in metadata:
                metadata[symbol] = {
                    "chokepoint_node": node["node"],
                    "chokepoint_holder": node["chokepoint_holder"],
                    "chokepoint_reason": reasons.get(node["node"], ""),
                }
    return metadata


def _annotate_targets_with_chokepoint_context(targets: list[dict], context: dict) -> None:
    by_symbol = {}
    for node in context["nodes"]:
        for record in node.get("a_share") or []:
            symbol = record.get("code")
            if symbol and symbol not in by_symbol:
                by_symbol[symbol] = node
    for target in targets:
        node = by_symbol.get(target.get("symbol"))
        if not node:
            continue
        target["chokepoint_node"] = node["node"]
        target["chokepoint_holder"] = node["chokepoint_holder"]
        target["chokepoint_reason"] = context["reasons"].get(node["node"], "")


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
    counts = {
        "pending": pending_count,
        "analyzed": 0,
        "skipped_stale": 0,
        "skipped_failed": 0,
        "skipped_weak_logic": 0,
        "skipped_rejected_logic": 0,
    }
    rows = store.connection.execute(
        """
        select state, count(*) as count
        from signal_analysis_state
        where state in ('analyzed', 'skipped_stale', 'skipped_failed', 'skipped_weak_logic', 'skipped_rejected_logic')
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


def _analysis_skip_state(evidence_status: str) -> str:
    if evidence_status == "weak":
        return "skipped_weak_logic"
    return "skipped_rejected_logic"


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
        selected = _select_with_optional_chokepoint_nodes(
            triage_selector,
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


def _select_with_optional_chokepoint_nodes(
    triage_selector,
    candidate_clusters,
    top_k: int,
    *,
    total_clusters: int,
    candidate_limit: int,
):
    kwargs = {"total_clusters": total_clusters, "candidate_limit": candidate_limit}
    if _selector_accepts_chokepoint_nodes(triage_selector):
        kwargs["chokepoint_nodes"] = _load_triage_chokepoint_nodes()
    return triage_selector.select(candidate_clusters, top_k, **kwargs)


def _selector_accepts_chokepoint_nodes(triage_selector) -> bool:
    try:
        parameters = inspect.signature(triage_selector.select).parameters
    except (AttributeError, TypeError, ValueError):
        return False
    return "chokepoint_nodes" in parameters


def _load_triage_chokepoint_nodes() -> list[dict]:
    try:
        return curated_nodes()
    except Exception:  # noqa: BLE001 - node context is a soft ranking hint, not a pipeline gate.
        return []


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
