from __future__ import annotations

import re

from news_contracts.schemas import load_contract_schema

from .schemas import (
    ADVERSARIAL_SCHEMA,
    COMPLETENESS_SCHEMA,
    FREE_GENERATION_SCHEMA,
    TARGET_PROPOSAL_SCHEMA,
)
from .transport import LlmProviderError


def enforce_free_generation_output(output: dict, allowed_signal_ids: set[str]) -> dict:
    _require_nonempty_text(output, "body")
    source_signal_ids = _require_string_list(output, "source_signal_ids")
    _enforce_provenance(source_signal_ids, allowed_signal_ids, "thesis.source_signal_ids")
    _require_enum(output, "direction", {"bullish", "bearish", "neutral", "mixed"})
    _require_enum(output, "confidence", {"low", "medium", "high"})
    _require_string_list(output, "uncertainty_tags")
    _require_string_list(output, "substantive_claims", allow_objects=True)
    for index, claim in enumerate(output.get("substantive_claims") or []):
        claim_source_ids = _require_string_list(claim, "source_signal_ids")
        _enforce_provenance(claim_source_ids, allowed_signal_ids, f"substantive_claims[{index}]")
        _require_nonempty_text(claim, "text")
    if output.get("transmission_path") is not None and not isinstance(output.get("transmission_path"), list):
        raise LlmProviderError("transmission_path must be an array or null")
    for index, step in enumerate(output.get("transmission_path") or []):
        step_source_ids = _require_string_list(step, "source_signal_ids")
        _enforce_provenance(step_source_ids, allowed_signal_ids, f"transmission_path[{index}]")
        _require_nonempty_text(step, "description")
    _require_nonempty_text(output, "falsifiable_expectation")
    _require_verification_window(output.get("verification_window"))
    return output


def enforce_completeness_output(output: dict) -> dict:
    notes = output.get("notes")
    if not isinstance(notes, list) or not any(str(note).strip() for note in notes):
        raise LlmProviderError("completeness critique requires non-empty notes")
    if output.get("body_unchanged") is not True:
        raise LlmProviderError("completeness critique requires body_unchanged true")
    output.setdefault("candidate_thesis_ids", [])
    return output


def enforce_adversarial_output(output: dict, body: str) -> dict:
    _require_nonempty_text(output, "strongest_counterargument")
    hedges = output.get("hedge_variables")
    if not isinstance(hedges, list) or not any(str(hedge).strip() for hedge in hedges):
        raise LlmProviderError("adversarial falsification requires non-empty hedge_variables")
    counter = output["strongest_counterargument"]
    if _is_hollow_counterargument(counter, body, hedges):
        raise LlmProviderError("adversarial counterargument is too hollow or echoes the thesis")
    output.setdefault("reviewer", "skeptic-reviewer")
    output.setdefault("review_run_id", "review-run-llm")
    return output


def enforce_target_candidates(payload: dict, symbol_universe: dict[str, str] | None = None) -> list[dict]:
    if not symbol_universe:
        raise LlmProviderError("target proposal requires explicit symbol_universe")
    candidates = payload.get("candidates")
    if not isinstance(candidates, list):
        raise LlmProviderError("target proposal requires candidates array")
    for index, candidate in enumerate(candidates):
        _require_nonempty_text(candidate, "symbol")
        if candidate["symbol"] not in symbol_universe:
            raise LlmProviderError(f"candidate symbol outside universe: {candidate['symbol']}")
        candidate["name"] = symbol_universe[candidate["symbol"]]
        logic = candidate.get("logic_score") or {}
        score = logic.get("score")
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not 0 <= score <= 100:
            raise LlmProviderError(f"candidate {candidate['symbol']} logic_score.score out of range")
        _require_nonempty_text(logic, "rationale")
        buy_point = candidate.get("buy_point") or {}
        if buy_point.get("status") not in {"favorable", "neutral", "unfavorable"}:
            raise LlmProviderError(f"candidate {candidate['symbol']} buy_point.status is invalid")
        _require_nonempty_text(buy_point, "rationale")
        _require_descriptions_if_present(candidate.get("catalysts"), f"candidates[{index}].catalysts")
        _require_descriptions_if_present(candidate.get("exit_triggers"), f"candidates[{index}].exit_triggers")
    return candidates


def schema_allowed_fields() -> dict[str, set[str]]:
    thesis_fields = set(load_contract_schema("thesis-contract")["properties"])
    target_fields = set(load_contract_schema("target-contract")["properties"])
    return {
        "free_generation": set(FREE_GENERATION_SCHEMA["properties"]) - (thesis_fields | {"falsifiable_expectation", "verification_window"}),
        "completeness_critique": set(COMPLETENESS_SCHEMA["properties"]) - {"notes", "candidate_thesis_ids", "body_unchanged"},
        "adversarial_falsification": set(ADVERSARIAL_SCHEMA["properties"]) - {"reviewer", "review_run_id", "strongest_counterargument", "hedge_variables"},
        "target_proposal": set(TARGET_PROPOSAL_SCHEMA["properties"]["candidates"]["items"]["properties"]) - (target_fields | {"eligible"}),
    }


def _enforce_provenance(source_signal_ids: list[str], allowed_signal_ids: set[str], label: str) -> None:
    extra = set(source_signal_ids or []) - allowed_signal_ids
    if extra:
        raise LlmProviderError(f"{label} contains unknown source_signal_ids: {sorted(extra)}")


def _require_nonempty_text(record: dict, field_name: str) -> None:
    value = record.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise LlmProviderError(f"{field_name} is required")


def _require_enum(record: dict, field_name: str, allowed: set[str]) -> None:
    value = record.get(field_name)
    if value not in allowed:
        raise LlmProviderError(f"{field_name} must be one of {sorted(allowed)}")


def _require_string_list(record: dict, field_name: str, allow_objects: bool = False) -> list:
    value = record.get(field_name)
    if not isinstance(value, list):
        raise LlmProviderError(f"{field_name} must be an array")
    if allow_objects:
        return value
    if not all(isinstance(item, str) for item in value):
        raise LlmProviderError(f"{field_name} must contain only strings")
    return value


def _require_verification_window(value) -> None:
    if not isinstance(value, dict):
        raise LlmProviderError("verification_window is required")
    _require_nonempty_text(value, "start")
    _require_nonempty_text(value, "end")


def _require_descriptions_if_present(items, label: str) -> None:
    if items is None:
        return
    if not isinstance(items, list):
        raise LlmProviderError(f"{label} must be an array")
    if not items:
        return
    for item in items:
        if not isinstance(item, dict):
            raise LlmProviderError(f"{label} item requires description")
        _require_nonempty_text(item, "description")


def _is_hollow_counterargument(counterargument: str, body: str, hedge_variables: list[str]) -> bool:
    compact_counter = _compact(counterargument)
    compact_body = _compact(body)
    if len(compact_counter) < 30 or compact_counter in compact_body or compact_body in compact_counter:
        return True
    return not _has_specific_anchor(counterargument, hedge_variables)


def _has_specific_anchor(counterargument: str, hedge_variables: list[str]) -> bool:
    tokens = {token.lower() for token in re.findall(r"[A-Za-z][A-Za-z0-9-]{3,}|[一-龥]{2,}|\d+(?:\.\d+)?%?", counterargument)}
    hedge_tokens = {
        token.lower()
        for hedge in hedge_variables
        for token in re.findall(r"[A-Za-z][A-Za-z0-9-]{3,}|[一-龥]{2,}|\d+(?:\.\d+)?%?", str(hedge))
    }
    generic = {
        "thesis",
        "could",
        "wrong",
        "because",
        "things",
        "change",
        "risks",
        "exist",
        "market",
        "company",
        "business",
    }
    return bool((tokens - generic) & (hedge_tokens - generic))


def _compact(value: str) -> str:
    return re.sub(r"\s+", "", value.lower())
