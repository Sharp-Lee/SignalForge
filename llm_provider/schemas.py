from __future__ import annotations


CLAIM = {
    "type": "object",
    "additionalProperties": False,
    "required": ["text", "source_signal_ids"],
    "properties": {
        "text": {"type": "string"},
        "source_signal_ids": {"type": "array", "items": {"type": "string"}},
    },
}

TRANSMISSION_STEP = {
    "type": "object",
    "additionalProperties": False,
    "required": ["description", "source_signal_ids"],
    "properties": {
        "description": {"type": "string"},
        "source_signal_ids": {"type": "array", "items": {"type": "string"}},
    },
}

FREE_GENERATION_SCHEMA = {
    "title": "free_generation",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "body",
        "source_signal_ids",
        "substantive_claims",
        "direction",
        "confidence",
        "uncertainty_tags",
        "origin_market",
        "target_market",
        "transmission_path",
        "falsifiable_expectation",
        "verification_window",
    ],
    "properties": {
        "body": {"type": "string"},
        "source_signal_ids": {"type": "array", "items": {"type": "string"}},
        "substantive_claims": {"type": "array", "items": CLAIM},
        "direction": {"type": "string", "enum": ["bullish", "bearish", "neutral", "mixed"]},
        "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
        "uncertainty_tags": {"type": "array", "items": {"type": "string"}},
        "origin_market": {"type": ["string", "null"]},
        "target_market": {"type": ["string", "null"]},
        "transmission_path": {"type": ["array", "null"], "items": TRANSMISSION_STEP},
        "falsifiable_expectation": {"type": "string"},
        "verification_window": {
            "type": "object",
            "additionalProperties": False,
            "required": ["start", "end"],
            "properties": {
                "start": {"type": "string"},
                "end": {"type": "string"},
            },
        },
    },
}

COMPLETENESS_SCHEMA = {
    "title": "completeness_critique",
    "type": "object",
    "additionalProperties": False,
    "required": ["notes", "candidate_thesis_ids", "body_unchanged"],
    "properties": {
        "notes": {"type": "array", "items": {"type": "string"}},
        "candidate_thesis_ids": {"type": "array", "items": {"type": "string"}},
        "body_unchanged": {"type": "boolean"},
    },
}

ADVERSARIAL_SCHEMA = {
    "title": "adversarial_falsification",
    "type": "object",
    "additionalProperties": False,
    "required": ["reviewer", "review_run_id", "strongest_counterargument", "hedge_variables"],
    "properties": {
        "reviewer": {"type": "string"},
        "review_run_id": {"type": "string"},
        "strongest_counterargument": {"type": "string"},
        "hedge_variables": {"type": "array", "items": {"type": "string"}},
    },
}

TARGET_PROPOSAL_SCHEMA = {
    "title": "target_proposal",
    "type": "object",
    "additionalProperties": False,
    "required": ["candidates"],
    "properties": {
        "candidates": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "id",
                    "symbol",
                    "target_market",
                    "eligible",
                    "logic_score",
                    "buy_point",
                    "catalysts",
                    "exit_triggers",
                ],
                "properties": {
                    "id": {"type": "string"},
                    "symbol": {"type": "string"},
                    "target_market": {"type": "string"},
                    "eligible": {"type": "boolean"},
                    "logic_score": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["score", "rationale"],
                        "properties": {
                            "score": {"type": "integer"},
                            "rationale": {"type": "string"},
                        },
                    },
                    "buy_point": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["status", "rationale"],
                        "properties": {
                            "status": {"type": "string", "enum": ["favorable", "neutral", "unfavorable"]},
                            "rationale": {"type": "string"},
                        },
                    },
                    "catalysts": {
                        "type": "array",
                        "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["kind", "value", "description"],
                        "properties": {
                            "kind": {"type": ["string", "null"]},
                            "value": {"type": ["string", "null"]},
                            "description": {"type": "string"},
                        },
                        },
                    },
                    "exit_triggers": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["description"],
                            "properties": {"description": {"type": "string"}},
                        },
                    },
                },
            },
        }
    },
}


CLUSTER_TRIAGE_SCHEMA = {
    "title": "cluster_triage",
    "type": "object",
    "additionalProperties": False,
    "required": ["selected"],
    "properties": {
        "selected": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["cluster_id", "reason"],
                "properties": {
                    "cluster_id": {"type": "string"},
                    "reason": {"type": "string"},
                },
            },
        }
    },
}
