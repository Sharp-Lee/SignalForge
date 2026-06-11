from __future__ import annotations

from datetime import datetime


def create_freeform_thesis(thesis_id: str, body: str, source_signal_ids: list[str]) -> dict:
    return {
        "id": thesis_id,
        "body": body,
        "source_signal_ids": source_signal_ids,
        "substantive_claims": [],
        "status": "draft",
        "confidence": "low",
        "uncertainty_tags": [],
    }


def add_substantive_claim(
    thesis: dict,
    text: str,
    source_signal_ids: list[str] | None = None,
) -> dict:
    updated = dict(thesis)
    claims = list(updated.get("substantive_claims", []))
    claims.append({"text": text, "source_signal_ids": source_signal_ids or []})
    updated["substantive_claims"] = claims
    return updated


def add_transmission_step(
    thesis: dict,
    description: str,
    source_signal_ids: list[str] | None = None,
) -> dict:
    updated = dict(thesis)
    path = list(updated.get("transmission_path", []))
    path.append({"description": description, "source_signal_ids": source_signal_ids or []})
    updated["transmission_path"] = path
    return updated


def create_completeness_critique(
    thesis: dict,
    notes: list[str],
    candidate_thesis_ids: list[str],
) -> dict:
    updated = dict(thesis)
    updated["completeness_critique"] = {
        "notes": notes,
        "candidate_thesis_ids": candidate_thesis_ids,
        "body_unchanged": True,
    }
    return updated


def create_adversarial_review(
    thesis_author_id: str,
    author_persona: str,
    reviewer_instance_id: str,
    reviewer_persona: str,
    review_run_id: str,
    reviewer: str,
    strongest_counterargument: str,
    hedge_variables: list[str],
) -> dict:
    return {
        "reviewer": reviewer,
        "review_session": {
            "thesis_author_id": thesis_author_id,
            "author_persona": author_persona,
            "reviewer_instance_id": reviewer_instance_id,
            "reviewer_persona": reviewer_persona,
            "review_run_id": review_run_id,
        },
        "strongest_counterargument": strongest_counterargument,
        "hedge_variables": hedge_variables,
    }


def create_market_move_signal(
    signal_id: str,
    title: str,
    body: str,
    source: dict,
    raw_payload: dict,
    trigger_reason: dict,
) -> dict:
    return {
        "id": signal_id,
        "source": source,
        "title": title,
        "body": body,
        "signal_origin": "market_move",
        "type_tag": "other",
        "triage": {"excluded": False, "reasons": []},
        "raw_payload": raw_payload,
        "trigger_reason": trigger_reason,
    }


def create_track_record(
    direction: str,
    falsifiable_expectation: str,
    verification_window: dict,
    created_at: datetime,
) -> dict:
    return {
        "direction": direction,
        "falsifiable_expectation": falsifiable_expectation,
        "verification_window": verification_window,
        "created_at": created_at.isoformat().replace("+00:00", "Z"),
    }


def create_outcome_raw(
    thesis_id: str,
    observed_at: str,
    result: dict,
    maturity: dict,
) -> dict:
    return {
        "kind": "outcome_raw",
        "thesis_id": thesis_id,
        "observed_at": observed_at,
        "result": result,
        "maturity": maturity,
    }


def create_calibration_signal(outcome_raw: dict) -> dict | None:
    maturity = outcome_raw.get("maturity", {})
    if not (
        maturity.get("verification_window_expired")
        or maturity.get("event_occurred")
        or maturity.get("confidence_sufficient")
    ):
        return None
    return {
        "kind": "calibration_signal",
        "thesis_id": outcome_raw["thesis_id"],
        "observed_at": outcome_raw["observed_at"],
        "result": outcome_raw["result"],
        "maturity": maturity,
    }


def create_human_decision(
    subject_type: str,
    subject_id: str,
    decision: str,
    reason: str,
    decided_at: str,
) -> dict:
    return {
        "subject_type": subject_type,
        "subject_id": subject_id,
        "decision": decision,
        "reason": reason,
        "decided_at": decided_at,
    }


def create_empty_recommendation(period: str, reasons: list[str]) -> dict:
    return {
        "kind": "empty_recommendation",
        "period": period,
        "targets": [],
        "reasons": reasons,
    }


def update_target_state(target: dict, satisfied_catalysts: list[str]) -> dict:
    updated = dict(target)
    if updated.get("state") != "watch":
        return updated
    descriptions = [item.get("description", "") for item in updated.get("catalysts", [])]
    if any(
        satisfied in description
        for satisfied in satisfied_catalysts
        for description in descriptions
    ):
        updated["state"] = "review-required"
        updated["needs_review"] = True
    return updated
