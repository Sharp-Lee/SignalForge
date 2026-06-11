from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from hashlib import sha256
import html
import re
from typing import Iterable

from jsonschema import Draft202012Validator

from .schemas import load_contract_schema


class ContractError(ValueError):
    """Raised when a contract invariant is violated."""


class CalibrationNotImplemented(NotImplementedError):
    """Raised until feedback calibration is implemented in a later change."""


@dataclass
class ValidationResult:
    accepted: bool
    record: dict | None = None
    reason: str | None = None
    duplicate_of: str | None = None
    triage_reasons: list[str] = field(default_factory=list)
    pending_verification_claims: list[str] = field(default_factory=list)


TYPE_TAGS = {
    "supply_demand_bottleneck",
    "policy",
    "weather_climate",
    "export_control_geopolitics",
    "technology_inflection",
    "other",
}
SIGNAL_ORIGINS = {"news", "market_move", "last30days_attention"}

DEFAULT_DEDUP_THRESHOLD = 0.14
DEFAULT_TRIAGE_STRATEGY = "zh_cn_heuristic_v0"


def validate_signal(
    signal: dict,
    existing: Iterable[dict] | None = None,
    dedup_threshold: float = DEFAULT_DEDUP_THRESHOLD,
    triage_strategy: str = DEFAULT_TRIAGE_STRATEGY,
) -> ValidationResult:
    record = dict(signal)
    _validate_schema("signal-contract", record)
    source = dict(record.get("source") or {})
    if record.get("signal_origin") not in SIGNAL_ORIGINS:
        raise ContractError("signal signal_origin is invalid")
    if record.get("type_tag") not in TYPE_TAGS:
        raise ContractError("signal type_tag is invalid")
    if record.get("signal_origin") == "market_move":
        _validate_event_trigger_reason(record.get("trigger_reason"))

    duplicate_of = _find_near_duplicate(record, existing or [], threshold=dedup_threshold)
    if duplicate_of:
        return ValidationResult(False, reason="near_duplicate", duplicate_of=duplicate_of)

    triage_reasons = _lightweight_triage(record, strategy=triage_strategy)
    if triage_reasons:
        record["triage"] = {"excluded": True, "reasons": triage_reasons, "strategy": triage_strategy}
        return ValidationResult(
            False,
            record=record,
            reason="lightweight_triage",
            triage_reasons=triage_reasons,
        )

    record["source"] = source
    record["route"] = record["type_tag"]
    record.setdefault("triage", {"excluded": False, "reasons": [], "strategy": triage_strategy})
    record["triage"].setdefault("strategy", triage_strategy)
    return ValidationResult(True, record=record)


def validate_thesis(thesis: dict) -> ValidationResult:
    record = dict(thesis)
    _validate_schema("thesis-contract", record)

    if record["status"] == "confirmed":
        critique = record.get("completeness_critique")
        if not critique:
            raise ContractError("confirmed thesis requires completeness_critique")
        if critique.get("body_unchanged") is not True:
            raise ContractError("completeness_critique must preserve body")
        if not record.get("adversarial_falsification"):
            raise ContractError("confirmed thesis requires adversarial_falsification")
        review = record["adversarial_falsification"]
        if not review.get("strongest_counterargument") or not review.get("hedge_variables"):
            raise ContractError("adversarial_falsification requires counterargument and hedge_variables")
        session = review.get("review_session") or {}
        if session.get("reviewer_instance_id") == session.get("thesis_author_id"):
            raise ContractError("confirmed thesis requires an independent reviewer instance")
        if session.get("reviewer_persona") == session.get("author_persona"):
            raise ContractError("confirmed thesis requires an independent reviewer persona")
        if not record.get("track_record"):
            raise ContractError("confirmed thesis requires track_record")

    pending_claims = []
    for claim in record.get("substantive_claims", []):
        if not claim.get("source_signal_ids"):
            pending_claims.append(claim.get("text", ""))
    for step in record.get("transmission_path", []):
        if not step.get("source_signal_ids"):
            pending_claims.append(step.get("description", ""))
    if pending_claims:
        record["pending_verification_claims"] = pending_claims

    uncertainty_tags = set(record.get("uncertainty_tags", []))
    source_count = len(record.get("source_signal_ids") or [])
    if source_count == 0:
        uncertainty_tags.add("no_source")
        record["confidence"] = "low"
    elif source_count == 1:
        uncertainty_tags.add("single_source")
        if record.get("confidence") == "high":
            record["confidence"] = "medium"
    record["uncertainty_tags"] = sorted(uncertainty_tags)

    return ValidationResult(True, record=record, pending_verification_claims=pending_claims)


def validate_target(target: dict, confirmed_thesis_ids: set[str] | None = None) -> ValidationResult:
    record = dict(target)
    if "total_score" in record and ("logic_score" not in record or "buy_point" not in record):
        raise ContractError("target rejects single total score; use logic_score and buy_point")
    _validate_schema("target-contract", record)

    thesis_ids = set(record.get("thesis_ids") or [])
    confirmed = confirmed_thesis_ids or set()
    if not thesis_ids or not thesis_ids.issubset(confirmed):
        raise ContractError("target requires at least one confirmed thesis")

    if not record.get("catalysts") or not record.get("exit_triggers"):
        raise ContractError("target requires at least one catalyst and exit trigger")

    buy_point = record.get("buy_point") or {}
    if buy_point.get("status") == "unfavorable" and record.get("state") in {"buy-zone", "hold"}:
        raise ContractError("unfavorable buy_point cannot be presented as now buy")

    priced_in = dict(record.get("priced_in") or {})
    price_change = buy_point.get("price_change_since_signal", priced_in.get("price_change_since_signal", 0))
    if price_change is not None and price_change >= 0.3:
        priced_in["risk"] = "high"
    record["priced_in"] = priced_in

    return ValidationResult(True, record=record)


def dedup_hash(record: dict) -> str:
    material = f"{record.get('title', '')}\n{record.get('body', '')}".lower().strip()
    return sha256(material.encode("utf-8")).hexdigest()


def _find_near_duplicate(signal: dict, existing: Iterable[dict], threshold: float = DEFAULT_DEDUP_THRESHOLD) -> str | None:
    # Prefer false negatives over false positives: losing a distinct signal is harder to recover than missing a rewrite.
    body = signal.get("body", "")
    for candidate in existing:
        if _jaccard(body, candidate.get("body", "")) >= threshold:
            return candidate.get("id")
    return None


def _lightweight_triage(signal: dict, strategy: str = DEFAULT_TRIAGE_STRATEGY) -> list[str]:
    if strategy != DEFAULT_TRIAGE_STRATEGY:
        raise ContractError(f"unknown triage strategy: {strategy}")
    text = f"{signal.get('title', '')}\n{signal.get('body', '')}"
    reasons = []
    if any(term in text for term in ("将出台", "计划", "研究", "拟", "考虑")):
        reasons.append("time_vague")
    if any(term in text for term in ("有关", "相关", "涉及领域", "等")):
        reasons.append("content_vague")
    if not _has_tradable_impact_anchor(text):
        reasons.append("impact_vague")
    if len(text.strip()) < 18:
        reasons.append("low_signal_noise")
    return reasons if len(reasons) >= 2 else []


def _jaccard(left: str, right: str) -> float:
    left_tokens = _dedup_tokens(left)
    right_tokens = _dedup_tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def _dedup_tokens(value: str) -> set[str]:
    normalized = _normalize_dedup_text(value)
    if _cjk_ratio(normalized) >= 0.20:
        return _char_bigrams(normalized)
    return _word_shingles(normalized)


def _normalize_dedup_text(value: str) -> str:
    unescaped = html.unescape(value or "")
    without_tags = re.sub(r"<[^>]+>", " ", unescaped)
    return re.sub(r"\s+", " ", without_tags).strip()


def _cjk_ratio(value: str) -> float:
    compact = [char for char in value if not char.isspace()]
    if not compact:
        return 0.0
    cjk_count = sum(1 for char in compact if _is_cjk_unified(char))
    # Mixed-language text is routed by ratio: light Chinese annotations stay word-shingle, Chinese-heavy text uses char bigrams.
    return cjk_count / len(compact)


def _is_cjk_unified(char: str) -> bool:
    return "\u4e00" <= char <= "\u9fff"


def _char_bigrams(value: str) -> set[str]:
    compact = "".join(value.lower().split())
    if len(compact) < 2:
        return {compact} if compact else set()
    return {compact[index : index + 2] for index in range(len(compact) - 1)}


def _word_shingles(value: str) -> set[str]:
    tokens = re.findall(r"[a-z0-9]+", value.lower())
    if len(tokens) < 2:
        return set(tokens)
    return {" ".join(tokens[index : index + 2]) for index in range(len(tokens) - 1)}


def parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _has_tradable_impact_anchor(text: str) -> bool:
    patterns = (
        r"\d+(\.\d+)?\s*%",
        r"\d+(\.\d+)?\s*(亿|万|元|美元|人民币|吨|台|套|辆|股|MW|GW|GWh|MWh)",
        r"(Q[1-4]|[一二三四]季度|季度|月|周|日|年|天|202\d|203\d)",
        r"(长江流域|全国|欧洲|美国|中国|日本|韩国|东南亚|中东|明确范围)",
    )
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def _validate_schema(contract_name: str, record: dict) -> None:
    schema = load_contract_schema(contract_name)
    errors = sorted(Draft202012Validator(schema).iter_errors(record), key=lambda error: list(error.path))
    if not errors:
        return
    error = errors[0]
    path = ".".join(str(part) for part in error.path)
    location = f" at {path}" if path else ""
    raise ContractError(f"{contract_name} schema error{location}: {error.message}")


def _validate_event_trigger_reason(trigger_reason: dict | None) -> None:
    if not trigger_reason:
        raise ContractError("market_move signal requires trigger_reason")
    gates = (
        "source_strength",
        "quantified_impact",
        "cross_market_transmission",
        "significant_market_move",
    )
    if not any(trigger_reason.get(gate) for gate in gates):
        raise ContractError("trigger_reason must pass at least one event hard gate")
    if not trigger_reason.get("summary"):
        raise ContractError("trigger_reason summary is required")
