from __future__ import annotations


CANONICAL_LOGIC_TYPES = (
    "supply_demand",
    "substitution",
    "optimization",
    "policy_market_reform",
    "penetration",
    "margin_spread_repricing",
    "technology_route_shift",
    "policy_constraint_shock",
    "business_model_shift",
    "investment_order_cycle",
    "competitive_structure",
    "market_access_expansion",
    "asset_capital_revaluation",
    "fundamental_delivery_inflection",
)


_STRING_ARRAY = {
    "type": "array",
    "items": {"type": "string", "minLength": 1},
}


INVESTMENT_REASONING_AUDIT_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "investment_reasoning_audit",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "source_signal_ids",
        "primary_logic_type",
        "secondary_logic_types",
        "evidence_status",
        "premise",
        "upward_validation",
        "transmission_chain",
        "downstream_decomposition",
        "chokepoint_candidates",
        "target_search_decision",
        "missing_evidence",
        "disconfirming_evidence",
        "public_caveat",
    ],
    "properties": {
        "source_signal_ids": _STRING_ARRAY,
        "primary_logic_type": {"type": "string", "enum": list(CANONICAL_LOGIC_TYPES)},
        "secondary_logic_types": {
            "type": "array",
            "items": {"type": "string", "enum": list(CANONICAL_LOGIC_TYPES)},
        },
        "evidence_status": {"type": "string", "enum": ["accepted", "weak", "rejected"]},
        "premise": {"type": "string", "minLength": 1},
        "upward_validation": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["question", "answer", "evidence", "status"],
                "properties": {
                    "question": {"type": "string", "minLength": 1},
                    "answer": {"type": "string", "minLength": 1},
                    "evidence": _STRING_ARRAY,
                    "status": {"type": "string", "enum": ["supported", "partial", "unsupported", "unknown"]},
                },
            },
        },
        "transmission_chain": _STRING_ARRAY,
        "downstream_decomposition": _STRING_ARRAY,
        "chokepoint_candidates": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["node", "reason"],
                "properties": {
                    "node": {"type": "string", "minLength": 1},
                    "reason": {"type": "string", "minLength": 1},
                },
            },
        },
        "target_search_decision": {
            "type": "object",
            "additionalProperties": False,
            "required": ["status", "reason"],
            "properties": {
                "status": {"type": "string", "enum": ["allowed", "not_ready", "blocked"]},
                "reason": {"type": "string", "minLength": 1},
            },
        },
        "missing_evidence": _STRING_ARRAY,
        "disconfirming_evidence": _STRING_ARRAY,
        "public_caveat": {"type": "string", "minLength": 1},
    },
}
