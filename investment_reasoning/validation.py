from __future__ import annotations

from copy import deepcopy
import re
from typing import Iterable

from jsonschema import Draft202012Validator

from .schemas import CANONICAL_LOGIC_TYPES, INVESTMENT_REASONING_AUDIT_SCHEMA


class InvestmentReasoningError(ValueError):
    """Raised when an investment reasoning audit violates the contract."""


_SCHEMA_VALIDATOR = Draft202012Validator(INVESTMENT_REASONING_AUDIT_SCHEMA)
_CANONICAL_LOGIC_TYPES = set(CANONICAL_LOGIC_TYPES)


def validate_investment_reasoning_audit(
    audit: dict,
    *,
    allowed_signal_ids: Iterable[str] | None = None,
) -> dict:
    """Validate an investment reasoning audit and return a defensive copy."""

    record = deepcopy(audit)
    _validate_logic_types(record)
    _validate_schema(record)
    _validate_source_ids(record, set(allowed_signal_ids) if allowed_signal_ids is not None else None)
    _validate_target_gate(record)
    _validate_public_caveat(record["public_caveat"])
    return record


def _validate_schema(record: dict) -> None:
    errors = sorted(_SCHEMA_VALIDATOR.iter_errors(record), key=lambda error: list(error.path))
    if not errors:
        return
    error = errors[0]
    path = ".".join(str(part) for part in error.path) or "<root>"
    raise InvestmentReasoningError(f"investment reasoning schema error at {path}: {error.message}")


def _validate_logic_types(record: dict) -> None:
    primary = record.get("primary_logic_type")
    if primary is None:
        return
    if primary not in _CANONICAL_LOGIC_TYPES:
        raise InvestmentReasoningError(f"unknown primary_logic_type: {primary}")
    secondary = list(record.get("secondary_logic_types") or [])
    unknown = sorted(set(secondary) - _CANONICAL_LOGIC_TYPES)
    if unknown:
        raise InvestmentReasoningError(f"unknown secondary_logic_types: {unknown}")
    if primary in secondary:
        raise InvestmentReasoningError("secondary_logic_types duplicate primary_logic_type")
    if len(secondary) != len(set(secondary)):
        raise InvestmentReasoningError("secondary_logic_types contains duplicate values")


def _validate_source_ids(record: dict, allowed_signal_ids: set[str] | None) -> None:
    if allowed_signal_ids is None:
        return
    referenced = set(record.get("source_signal_ids") or [])
    for item in record.get("upward_validation") or []:
        referenced.update(item.get("evidence") or [])
    unknown = sorted(referenced - allowed_signal_ids)
    if unknown:
        raise InvestmentReasoningError(f"unknown source_signal_ids: {unknown}")


def _validate_target_gate(record: dict) -> None:
    evidence_status = record["evidence_status"]
    target_status = record["target_search_decision"]["status"]
    if evidence_status != "accepted" and target_status == "allowed":
        raise InvestmentReasoningError(f"{evidence_status} logic cannot allow target search")
    if target_status == "allowed":
        if evidence_status != "accepted":
            raise InvestmentReasoningError("target search requires accepted evidence")
        if not record.get("transmission_chain"):
            raise InvestmentReasoningError("allowed target search requires transmission_chain")
        if not record.get("downstream_decomposition"):
            raise InvestmentReasoningError("allowed target search requires downstream_decomposition")


def _validate_public_caveat(public_caveat: str) -> None:
    banned = [
        r"建议\s*买入",
        r"推荐",
        r"目标价",
        r"确定性机会",
        r"\bbuy\b",
        r"\brecommend(?:ed|ation)?\b",
        r"\btarget price\b",
        r"\bsure opportunity\b",
    ]
    for pattern in banned:
        if re.search(pattern, public_caveat, flags=re.IGNORECASE):
            raise InvestmentReasoningError("public_caveat contains recommendation language")
