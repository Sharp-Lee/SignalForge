from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha1
from typing import Any, Protocol

from llm_provider import (
    ADVERSARIAL_SCHEMA,
    COMPLETENESS_SCHEMA,
    FREE_GENERATION_SCHEMA,
    INVESTMENT_REASONING_SCHEMA,
    AnthropicCompletion,
    Completion,
    LlmProviderError,
    enforce_adversarial_output,
    enforce_completeness_output,
    enforce_free_generation_output,
    enforce_investment_reasoning_output,
)
from llm_provider.prompts import AUTHOR_SYSTEM, CRITIQUE_SYSTEM, REASONING_SYSTEM, REVIEWER_SYSTEM, render_reasoner_user
from news_contracts.interfaces import create_adversarial_review


class AnalysisOrchestrationError(ValueError):
    """Raised when analysis orchestration cannot produce a valid thesis candidate."""


class AnalysisSkipped(AnalysisOrchestrationError):
    """Raised when investment reasoning marks a signal cluster non-actionable."""

    def __init__(self, message: str, *, evidence_status: str, investment_reasoning: dict):
        super().__init__(message)
        self.evidence_status = evidence_status
        self.investment_reasoning = investment_reasoning


@dataclass(frozen=True)
class ReasonerIdentity:
    instance_id: str
    persona: str


class Reasoner(Protocol):
    identity: ReasonerIdentity

    def reason(self, role: str, context: dict[str, Any]) -> dict[str, Any]:
        ...


@dataclass
class AnalysisResult:
    thesis_id: str
    thesis: dict
    investment_reasoning: dict


class StubReasoner:
    def __init__(self, identity: ReasonerIdentity, responses: dict[str, dict[str, Any]]):
        self.identity = identity
        self.responses = responses
        self.calls: list[dict[str, Any]] = []

    def reason(self, role: str, context: dict[str, Any]) -> dict[str, Any]:
        self.calls.append({"role": role, "context": context})
        if role not in self.responses:
            raise AnalysisOrchestrationError(f"missing stub response for role {role}")
        return dict(self.responses[role])


class LlmReasoner:
    """Claude-backed reasoner boundary."""

    def __init__(
        self,
        identity: ReasonerIdentity,
        system_prompt: str | None = None,
        transport: Completion | None = None,
        max_tokens: int = 8000,
    ):
        self.identity = identity
        self.system_prompt = system_prompt
        self.transport = transport or AnthropicCompletion()
        self.max_tokens = max_tokens

    def reason(self, role: str, context: dict[str, Any]) -> dict[str, Any]:
        if role == "investment_reasoning":
            schema = INVESTMENT_REASONING_SCHEMA
            system = self.system_prompt or REASONING_SYSTEM
            thinking = {"type": "adaptive"}
        elif role == "free_generation":
            schema = FREE_GENERATION_SCHEMA
            system = self.system_prompt or AUTHOR_SYSTEM
            thinking = {"type": "adaptive"}
        elif role == "completeness_critique":
            schema = COMPLETENESS_SCHEMA
            system = self.system_prompt or CRITIQUE_SYSTEM
            thinking = None
        elif role == "adversarial_falsification":
            schema = ADVERSARIAL_SCHEMA
            system = self.system_prompt or REVIEWER_SYSTEM
            thinking = {"type": "adaptive"}
        else:
            raise LlmProviderError(f"unknown reasoner role: {role}")

        output = self.transport(
            system=system,
            user=render_reasoner_user(role, context),
            schema=schema,
            max_tokens=self.max_tokens,
            thinking=thinking,
        )
        if role == "investment_reasoning":
            return enforce_investment_reasoning_output(output, set(context.get("source_signal_ids") or []))
        if role == "free_generation":
            return enforce_free_generation_output(output, set(context.get("source_signal_ids") or []))
        if role == "completeness_critique":
            return enforce_completeness_output(output)
        return enforce_adversarial_output(output, context.get("body", ""))


def analyze(
    signals: list[dict],
    author_reasoner: Reasoner,
    reviewer_reasoner: Reasoner,
    store,
    *,
    thesis_id: str | None = None,
    created_at: datetime | None = None,
    verification_days: int = 90,
) -> AnalysisResult:
    _ensure_independent_reasoners(author_reasoner.identity, reviewer_reasoner.identity)
    if not signals:
        raise AnalysisOrchestrationError("analysis requires at least one source signal")

    created = created_at or datetime.now(UTC)
    source_signal_ids = [signal["id"] for signal in signals]
    base_context = {"signals": signals, "source_signal_ids": source_signal_ids}

    investment_reasoning = author_reasoner.reason("investment_reasoning", base_context)
    _ensure_actionable_reasoning(investment_reasoning)

    free = author_reasoner.reason(
        "free_generation",
        {**base_context, "investment_reasoning": investment_reasoning},
    )
    body = _required_text(free, "body", "free_generation")

    critique = author_reasoner.reason(
        "completeness_critique",
        {**base_context, "body": body},
    )
    critique_record = _build_completeness_critique(critique)

    adversarial = reviewer_reasoner.reason(
        "adversarial_falsification",
        {**base_context, "body": body, "completeness_critique": critique_record},
    )
    adversarial_record = _build_adversarial_review(
        adversarial,
        author_reasoner.identity,
        reviewer_reasoner.identity,
    )

    direction = free["direction"]
    thesis = {
        "id": thesis_id or _derive_thesis_id(body, source_signal_ids),
        "body": body,
        "source_signal_ids": free.get("source_signal_ids") or [],
        "substantive_claims": list(free.get("substantive_claims") or []),
        "direction": direction,
        "status": "confirmed",
        "confidence": free["confidence"],
        "uncertainty_tags": list(free.get("uncertainty_tags") or []),
        "completeness_critique": critique_record,
        "adversarial_falsification": adversarial_record,
        "track_record": _build_track_record(free, direction, created, verification_days),
        "investment_reasoning": investment_reasoning,
    }
    for optional_field in ("origin_market", "target_market", "transmission_path"):
        if free.get(optional_field) is not None:
            thesis[optional_field] = free[optional_field]

    stored_id = store.add_thesis(thesis)
    return AnalysisResult(thesis_id=stored_id, thesis=thesis, investment_reasoning=investment_reasoning)


def _ensure_independent_reasoners(author: ReasonerIdentity, reviewer: ReasonerIdentity) -> None:
    if reviewer.instance_id == author.instance_id:
        raise AnalysisOrchestrationError("reviewer instance must differ from author instance")
    if reviewer.persona == author.persona:
        raise AnalysisOrchestrationError("reviewer persona must differ from author persona")


def _ensure_actionable_reasoning(audit: dict) -> None:
    evidence_status = audit.get("evidence_status")
    target_status = (audit.get("target_search_decision") or {}).get("status")
    if evidence_status == "accepted" and target_status == "allowed":
        return
    reason = (audit.get("target_search_decision") or {}).get("reason") or "investment reasoning gate blocked analysis"
    raise AnalysisSkipped(
        f"investment reasoning {evidence_status or 'unknown'}: {reason}",
        evidence_status=evidence_status or "rejected",
        investment_reasoning=audit,
    )


def _build_completeness_critique(response: dict[str, Any]) -> dict:
    notes = response.get("notes")
    if not notes:
        raise AnalysisOrchestrationError("completeness critique requires notes")
    if response.get("body_unchanged") is not True:
        raise AnalysisOrchestrationError("completeness critique requires body_unchanged true")
    return {
        "notes": list(notes),
        "candidate_thesis_ids": list(response.get("candidate_thesis_ids") or []),
        "body_unchanged": True,
    }


def _build_adversarial_review(
    response: dict[str, Any],
    author: ReasonerIdentity,
    reviewer: ReasonerIdentity,
) -> dict:
    strongest = _required_text(response, "strongest_counterargument", "adversarial_falsification")
    hedges = response.get("hedge_variables")
    if not hedges:
        raise AnalysisOrchestrationError("adversarial falsification requires hedge_variables")
    return create_adversarial_review(
        thesis_author_id=author.instance_id,
        author_persona=author.persona,
        reviewer_instance_id=reviewer.instance_id,
        reviewer_persona=reviewer.persona,
        review_run_id=response.get("review_run_id") or _derive_review_run_id(strongest),
        reviewer=response.get("reviewer") or reviewer.persona,
        strongest_counterargument=strongest,
        hedge_variables=list(hedges),
    )


def _build_track_record(
    free_generation: dict[str, Any],
    direction: str,
    created_at: datetime,
    verification_days: int,
) -> dict:
    return {
        "direction": direction,
        "falsifiable_expectation": free_generation["falsifiable_expectation"],
        "verification_window": free_generation["verification_window"],
        "created_at": created_at.isoformat().replace("+00:00", "Z"),
    }


def _required_text(response: dict[str, Any], field_name: str, role: str) -> str:
    value = response.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise AnalysisOrchestrationError(f"{role} requires {field_name}")
    return value


def _derive_thesis_id(body: str, source_signal_ids: list[str]) -> str:
    digest = sha1((body + "|".join(source_signal_ids)).encode("utf-8")).hexdigest()[:12]
    return f"thesis-{digest}"


def _derive_review_run_id(counterargument: str) -> str:
    return f"review-{sha1(counterargument.encode('utf-8')).hexdigest()[:12]}"
