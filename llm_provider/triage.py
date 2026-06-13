from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from .prompts import render_cluster_triage_system, render_cluster_triage_user
from .schemas import CLUSTER_TRIAGE_SCHEMA
from .transport import Completion
from .validation import enforce_cluster_triage_output


@dataclass(frozen=True)
class TriageSelection:
    cluster_id: str
    reason: str


class LlmClusterTriageSelector:
    def __init__(self, transport: Completion, max_tokens: int = 1400):
        self.transport = transport
        self.max_tokens = max_tokens

    def select(
        self,
        clusters,
        top_k: int,
        *,
        total_clusters: int | None = None,
        candidate_limit: int | None = None,
        chokepoint_nodes: list[dict] | None = None,
    ) -> list[TriageSelection]:
        compact_clusters = [_compact_cluster(cluster) for cluster in clusters]
        compact_nodes = [_compact_chokepoint_node(node) for node in (chokepoint_nodes or [])]
        output = self.transport(
            system=render_cluster_triage_system(chokepoint_nodes=compact_nodes),
            user=render_cluster_triage_user(
                clusters=compact_clusters,
                top_k=top_k,
                total_clusters=total_clusters if total_clusters is not None else len(compact_clusters),
                candidate_limit=candidate_limit if candidate_limit is not None else len(compact_clusters),
                chokepoint_nodes=compact_nodes,
            ),
            schema=CLUSTER_TRIAGE_SCHEMA,
            max_tokens=self.max_tokens,
            thinking=None,
        )
        allowed = {cluster.id for cluster in clusters}
        selected = enforce_cluster_triage_output(output, allowed)
        return [TriageSelection(item["cluster_id"], item["reason"]) for item in selected[:top_k]]


def _compact_cluster(cluster) -> dict:
    signals = sorted(cluster.signals, key=_signal_datetime, reverse=True)
    return {
        "cluster_id": cluster.id,
        "newest_at": _to_iso(max((_signal_datetime(signal) for signal in signals), default=_min_datetime())),
        "signal_count": len(signals),
        "cluster_reason": cluster.reason,
        "signals": [_compact_signal(signal) for signal in signals[:3]],
    }


def _compact_signal(signal: dict) -> dict:
    source = signal.get("source") or {}
    body = signal.get("body") or ""
    return {
        "signal_id": signal.get("id"),
        "source": source.get("name") or source.get("id"),
        "published_at": source.get("published_at"),
        "title": signal.get("title"),
        "summary": body[:320],
    }


def _compact_chokepoint_node(node: dict) -> dict:
    return {
        "node": node.get("node"),
        "chokepoint_holder": node.get("chokepoint_holder"),
        "triggers": list(node.get("triggers") or []),
    }


def _signal_datetime(signal: dict) -> datetime:
    source = signal.get("source") or {}
    return _parse_datetime(source.get("published_at") or signal.get("published_at"))


def _parse_datetime(value: str | None) -> datetime:
    if not value:
        return _min_datetime()
    try:
        if value.endswith("Z"):
            return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
        return datetime.fromisoformat(value).astimezone(UTC)
    except (TypeError, ValueError):
        return _min_datetime()


def _min_datetime() -> datetime:
    return datetime.min.replace(tzinfo=UTC)


def _to_iso(value: datetime) -> str:
    return value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
