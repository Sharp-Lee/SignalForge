from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import html
import math
import re
from typing import Protocol


CJK_RATIO_CUTOFF = 0.20
ENGLISH_SHARED_TERM_THRESHOLD = 4
CHINESE_SHARED_TERM_THRESHOLD = 8
MIXED_SHARED_TERM_THRESHOLD = 4


@dataclass(frozen=True)
class SignalCluster:
    id: str
    signals: list[dict]
    reason: str


class SignalClusterer(Protocol):
    def cluster(self, signals: list[dict]) -> list[SignalCluster]:
        """Return stable pre-analysis signal clusters."""


@dataclass
class _SignalFeatures:
    signal: dict
    cjk_ratio: float
    english_terms: set[str]
    chinese_terms: set[str]
    alnum_terms: set[str]


class DefaultSignalClusterer:
    def cluster(self, signals: list[dict]) -> list[SignalCluster]:
        if not signals:
            return []

        features = self._features(signals)
        if len(features) == 1:
            return [_make_cluster(1, [features[0].signal], "singleton")]

        edges: dict[int, set[int]] = {index: set() for index in range(len(features))}
        edge_reasons: dict[tuple[int, int], str] = {}
        for left_index, left in enumerate(features):
            for right_index in range(left_index + 1, len(features)):
                related, reason = _relatedness(left, features[right_index])
                if related:
                    edges[left_index].add(right_index)
                    edges[right_index].add(left_index)
                    edge_reasons[(left_index, right_index)] = reason

        return _connected_components(signals, edges, edge_reasons)

    def _features(self, signals: list[dict]) -> list[_SignalFeatures]:
        raw = [_extract_raw_features(signal) for signal in signals]
        cutoff = math.ceil(len(signals) * 0.5)
        english = _df_filter([item.english_terms for item in raw], cutoff)
        chinese = _df_filter([item.chinese_terms for item in raw], cutoff)
        alnum = _df_filter([item.alnum_terms for item in raw], cutoff)
        return [
            _SignalFeatures(
                signal=item.signal,
                cjk_ratio=item.cjk_ratio,
                english_terms=english[index],
                chinese_terms=chinese[index],
                alnum_terms=alnum[index],
            )
            for index, item in enumerate(raw)
        ]


def _extract_raw_features(signal: dict) -> _SignalFeatures:
    text = _signal_text(signal)
    normalized = _normalize_text(text)
    return _SignalFeatures(
        signal=signal,
        cjk_ratio=_cjk_ratio(normalized),
        english_terms=_english_candidates(normalized),
        chinese_terms=_chinese_candidates(normalized),
        alnum_terms=_alnum_candidates(normalized),
    )


def _signal_text(signal: dict) -> str:
    return f"{signal.get('title', '')}\n{signal.get('body', '')}"


def _normalize_text(value: str) -> str:
    unescaped = html.unescape(value or "").replace("’", "'")
    without_tags = re.sub(r"<[^>]+>", " ", unescaped)
    return re.sub(r"\s+", " ", without_tags).strip()


def _cjk_ratio(value: str) -> float:
    compact = [char for char in value if not char.isspace()]
    if not compact:
        return 0.0
    cjk_count = sum(1 for char in compact if _is_cjk_unified(char))
    return cjk_count / len(compact)


def _is_cjk_unified(char: str) -> bool:
    return "\u4e00" <= char <= "\u9fff"


def _english_candidates(text: str) -> set[str]:
    terms: set[str] = set()
    for token in _shape_tokens(text):
        pieces = [token, *re.split(r"[-+.]", token)]
        for piece in pieces:
            normalized = _normalize_latin_term(piece)
            if not normalized:
                continue
            if _is_salient_english_shape(piece):
                terms.add(normalized)
    return terms


def _chinese_candidates(text: str) -> set[str]:
    terms = _alnum_candidates(text)
    cjk_runs = re.findall(r"[\u4e00-\u9fff]+", text)
    for run in cjk_runs:
        for size in (3, 4, 5):
            for index in range(max(0, len(run) - size + 1)):
                terms.add(run[index : index + size])
    return terms


def _alnum_candidates(text: str) -> set[str]:
    return {
        normalized
        for token in _shape_tokens(text)
        if (normalized := _normalize_latin_term(token))
        and (any(char.isdigit() for char in token) or token.isupper())
    }


def _shape_tokens(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9]+(?:[-+.][A-Za-z0-9]+)*", text)


def _normalize_latin_term(value: str) -> str:
    value = value.strip()
    if len(value) < 2:
        return ""
    normalized = value.lower()
    if normalized.endswith("'s"):
        normalized = normalized[:-2]
    if normalized.endswith("ies") and len(normalized) > 4:
        normalized = f"{normalized[:-3]}y"
    elif normalized.endswith("s") and len(normalized) > 4:
        normalized = normalized[:-1]
    return normalized


def _is_salient_english_shape(token: str) -> bool:
    if len(token) < 2:
        return False
    has_digit = any(char.isdigit() for char in token)
    all_caps = token.upper() == token and any(char.isalpha() for char in token) and len(token) >= 2
    title_like = token[:1].isupper() and any(char.islower() for char in token) and len(token) >= 3
    return has_digit or all_caps or title_like


def _df_filter(term_sets: list[set[str]], cutoff: int) -> list[set[str]]:
    frequencies = Counter(term for terms in term_sets for term in terms)
    return [{term for term in terms if frequencies[term] < cutoff} for terms in term_sets]


def _relatedness(left: _SignalFeatures, right: _SignalFeatures) -> tuple[bool, str]:
    if left.cjk_ratio >= CJK_RATIO_CUTOFF and right.cjk_ratio >= CJK_RATIO_CUTOFF:
        shared = left.chinese_terms & right.chinese_terms
        return (
            len(shared) >= CHINESE_SHARED_TERM_THRESHOLD,
            f"zh_shared_terms={len(shared)}",
        )
    if left.cjk_ratio < CJK_RATIO_CUTOFF and right.cjk_ratio < CJK_RATIO_CUTOFF:
        shared = left.english_terms & right.english_terms
        return (
            len(shared) >= ENGLISH_SHARED_TERM_THRESHOLD,
            f"en_shared_terms={len(shared)}",
        )
    shared = left.alnum_terms & right.alnum_terms
    return (
        len(shared) >= MIXED_SHARED_TERM_THRESHOLD,
        f"mixed_alnum_terms={len(shared)}",
    )


def _connected_components(
    signals: list[dict],
    edges: dict[int, set[int]],
    edge_reasons: dict[tuple[int, int], str],
) -> list[SignalCluster]:
    clusters: list[SignalCluster] = []
    seen: set[int] = set()
    for start in range(len(signals)):
        if start in seen:
            continue
        stack = [start]
        component: list[int] = []
        seen.add(start)
        while stack:
            current = stack.pop()
            component.append(current)
            for neighbor in sorted(edges[current], reverse=True):
                if neighbor not in seen:
                    seen.add(neighbor)
                    stack.append(neighbor)
        component.sort()
        clusters.append(_make_cluster(len(clusters) + 1, [signals[index] for index in component], _component_reason(component, edge_reasons)))
    return clusters


def _component_reason(component: list[int], edge_reasons: dict[tuple[int, int], str]) -> str:
    if len(component) == 1:
        return "singleton"
    reasons = []
    component_set = set(component)
    for (left, right), reason in sorted(edge_reasons.items()):
        if left in component_set and right in component_set:
            reasons.append(f"{left}->{right}:{reason}")
    return "; ".join(reasons) if reasons else "connected"


def _make_cluster(index: int, signals: list[dict], reason: str) -> SignalCluster:
    return SignalCluster(id=f"cluster-{index:03d}", signals=signals, reason=reason)
