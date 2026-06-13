from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha1
from typing import Any, Protocol

from llm_provider import (
    TARGET_PROPOSAL_SCHEMA,
    AnthropicCompletion,
    Completion,
    LlmProviderError,
    enforce_target_candidates,
)
from llm_provider.prompts import TARGET_SYSTEM, render_target_user
from news_contracts.interfaces import create_empty_recommendation


class TargetGenerationError(ValueError):
    """Raised when target generation cannot assemble a candidate."""


class TargetProposer(Protocol):
    def propose(self, thesis: dict) -> list[dict]:
        ...


class PriceLookup(Protocol):
    def price_change_since_signal(self, symbol: str, thesis: dict) -> float:
        ...


@dataclass
class TargetGenerationResult:
    target_ids: list[str]
    targets: list[dict]
    empty_recommendation: dict | None = None
    rejected_reasons: list[str] | None = None


class StubTargetProposer:
    def __init__(self, candidates: list[dict]):
        self.candidates = candidates
        self.calls: list[dict] = []

    def propose(self, thesis: dict) -> list[dict]:
        self.calls.append(thesis)
        return [dict(candidate) for candidate in self.candidates]


class StubPriceLookup:
    def __init__(self, price_changes: dict[str, float]):
        self.price_changes = price_changes
        self.calls: list[dict[str, Any]] = []

    def price_change_since_signal(self, symbol: str, thesis: dict) -> float:
        self.calls.append({"symbol": symbol, "thesis_id": thesis.get("id")})
        if symbol not in self.price_changes:
            raise TargetGenerationError(f"missing price change for {symbol}")
        return self.price_changes[symbol]


class LlmTargetProposer:
    """Claude-backed target proposer boundary."""

    def __init__(
        self,
        system_prompt: str | None = None,
        transport: Completion | None = None,
        symbol_universe: dict[str, str] | None = None,
        max_tokens: int = 8000,
    ):
        self.system_prompt = system_prompt or TARGET_SYSTEM
        self.transport = transport or AnthropicCompletion()
        self.symbol_universe = dict(symbol_universe) if symbol_universe is not None else None
        self.max_tokens = max_tokens

    def propose(self, thesis: dict) -> list[dict]:
        if self.symbol_universe is None:
            raise LlmProviderError("LlmTargetProposer requires explicit symbol_universe")
        payload = self.transport(
            system=self.system_prompt,
            user=render_target_user(thesis, self.symbol_universe),
            schema=TARGET_PROPOSAL_SCHEMA,
            max_tokens=self.max_tokens,
            thinking={"type": "adaptive"},
        )
        return enforce_target_candidates(payload, self.symbol_universe)


def propose_targets(
    thesis: dict,
    proposer: TargetProposer,
    price_lookup: PriceLookup,
    store,
    *,
    period: str = "current",
    min_logic_score: float = 60,
) -> TargetGenerationResult:
    target_ids: list[str] = []
    targets: list[dict] = []
    rejected_reasons: list[str] = []
    seen_symbols: set[str] = set()

    for candidate in proposer.propose(thesis):
        reason = _candidate_rejection_reason(candidate, min_logic_score)
        if reason:
            rejected_reasons.append(reason)
            continue

        symbol = _required_text(candidate, "symbol")
        if symbol in seen_symbols:
            rejected_reasons.append(f"{symbol}: duplicate symbol in thesis")
            continue
        seen_symbols.add(symbol)

        try:
            price_change = price_lookup.price_change_since_signal(symbol, thesis)
        except Exception as exc:
            rejected_reasons.append(str(exc))
            seen_symbols.remove(symbol)
            continue

        target = _assemble_target(thesis, candidate, price_change)
        target_id = store.add_target(target)
        target_ids.append(target_id)
        targets.append(target)

    if target_ids:
        return TargetGenerationResult(target_ids=target_ids, targets=targets, rejected_reasons=rejected_reasons)

    reasons = rejected_reasons or ["no qualified target candidates"]
    return TargetGenerationResult(
        target_ids=[],
        targets=[],
        empty_recommendation=create_empty_recommendation(period=period, reasons=reasons),
        rejected_reasons=reasons,
    )


def _candidate_rejection_reason(candidate: dict, min_logic_score: float) -> str | None:
    symbol = candidate.get("symbol") or "<unknown>"
    if candidate.get("eligible") is not True:
        return f"{symbol}: candidate not eligible"
    logic_score = candidate.get("logic_score") or {}
    if logic_score.get("score", -1) < min_logic_score:
        return f"{symbol}: logic score below threshold"
    if not candidate.get("catalysts"):
        return f"{symbol}: missing catalysts"
    if not candidate.get("exit_triggers"):
        return f"{symbol}: missing exit triggers"
    return None


def _assemble_target(thesis: dict, candidate: dict, price_change: float) -> dict:
    symbol = _required_text(candidate, "symbol")
    buy_point = dict(candidate.get("buy_point") or {})
    buy_point["price_change_since_signal"] = price_change
    target = {
        "id": _derive_target_id(symbol, thesis["id"]),
        "symbol": symbol,
        "name": _required_text(candidate, "name"),
        "target_market": candidate.get("target_market") or thesis.get("target_market") or "unknown",
        "thesis_ids": [thesis["id"]],
        "logic_score": dict(candidate.get("logic_score") or {}),
        "buy_point": buy_point,
        "state": "watch",
        "catalysts": [_drop_null(catalyst) for catalyst in candidate.get("catalysts") or []],
        "exit_triggers": [_drop_null(trigger) for trigger in candidate.get("exit_triggers") or []],
        "priced_in": {
            "price_change_since_signal": price_change,
            "risk": _priced_in_risk(price_change),
        },
    }
    for field_name in ("chokepoint_node", "chokepoint_holder", "chokepoint_reason"):
        value = candidate.get(field_name)
        if isinstance(value, str) and value.strip():
            target[field_name] = value.strip()
    return target


def _required_text(record: dict, field_name: str) -> str:
    value = record.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise TargetGenerationError(f"candidate requires {field_name}")
    return value


def _drop_null(record: dict) -> dict:
    return {key: value for key, value in record.items() if value is not None}


def _priced_in_risk(price_change: float) -> str:
    if price_change >= 0.3:
        return "high"
    if price_change >= 0.1:
        return "medium"
    return "low"


def _derive_target_id(symbol: str, thesis_id: str) -> str:
    digest = sha1(f"{symbol}|{thesis_id}".encode("utf-8")).hexdigest()[:12]
    return f"target-{digest}"
