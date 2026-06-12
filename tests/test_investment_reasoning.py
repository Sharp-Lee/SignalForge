import pytest
from jsonschema import Draft202012Validator, ValidationError

from investment_reasoning import (
    CANONICAL_LOGIC_TYPES,
    INVESTMENT_REASONING_AUDIT_SCHEMA,
    InvestmentReasoningError,
    validate_investment_reasoning_audit,
)


def valid_audit(**overrides):
    audit = {
        "source_signal_ids": ["sig-1"],
        "primary_logic_type": "supply_demand",
        "secondary_logic_types": ["margin_spread_repricing"],
        "evidence_status": "accepted",
        "premise": "HBM capacity tightness may indicate structurally high AI memory demand.",
        "upward_validation": [
            {
                "question": "Is terminal AI accelerator demand still expanding?",
                "answer": "Cloud capex and accelerator shipment signals support the premise.",
                "evidence": ["sig-1"],
                "status": "supported",
            }
        ],
        "transmission_chain": [
            "AI accelerator demand -> HBM content per accelerator -> HBM capacity tightness -> pricing power"
        ],
        "downstream_decomposition": [
            "Separate HBM makers, advanced packaging, TSV/test, equipment, and materials before looking for targets."
        ],
        "chokepoint_candidates": [
            {"node": "HBM advanced packaging", "reason": "Capacity and yield expansion can be slower than demand."}
        ],
        "target_search_decision": {
            "status": "allowed",
            "reason": "Evidence is accepted and bottleneck candidates are identified.",
        },
        "missing_evidence": ["Customer-level HBM order duration"],
        "disconfirming_evidence": ["AI capex cut", "HBM price reversal"],
        "public_caveat": "这是一条供需观察逻辑，仍取决于 AI capex 与 HBM 价格是否继续坚挺。",
    }
    audit.update(overrides)
    return audit


def test_schema_accepts_valid_reasoning_audit():
    Draft202012Validator(INVESTMENT_REASONING_AUDIT_SCHEMA).validate(valid_audit())


def test_schema_rejects_missing_required_primary_logic():
    audit = valid_audit()
    audit.pop("primary_logic_type")

    with pytest.raises(ValidationError):
        Draft202012Validator(INVESTMENT_REASONING_AUDIT_SCHEMA).validate(audit)


def test_validate_accepts_canonical_reasoning_audit():
    result = validate_investment_reasoning_audit(valid_audit(), allowed_signal_ids={"sig-1"})

    assert result["primary_logic_type"] == "supply_demand"
    assert "competitive_structure" in CANONICAL_LOGIC_TYPES


def test_validate_rejects_unknown_logic_type():
    with pytest.raises(InvestmentReasoningError, match="unknown primary_logic_type"):
        validate_investment_reasoning_audit(valid_audit(primary_logic_type="made_up_logic"))


def test_validate_rejects_secondary_logic_duplicate_or_unknown():
    with pytest.raises(InvestmentReasoningError, match="duplicate"):
        validate_investment_reasoning_audit(valid_audit(secondary_logic_types=["supply_demand"]))

    with pytest.raises(InvestmentReasoningError, match="unknown secondary_logic_types"):
        validate_investment_reasoning_audit(valid_audit(secondary_logic_types=["made_up_logic"]))


def test_weak_or_rejected_logic_cannot_allow_target_search():
    for evidence_status in ("weak", "rejected"):
        audit = valid_audit(evidence_status=evidence_status, target_search_decision={"status": "allowed", "reason": "try anyway"})

        with pytest.raises(InvestmentReasoningError, match="cannot allow target search"):
            validate_investment_reasoning_audit(audit)


def test_accepted_allowed_logic_requires_transmission_and_decomposition():
    with pytest.raises(InvestmentReasoningError, match="transmission_chain"):
        validate_investment_reasoning_audit(valid_audit(transmission_chain=[]))

    with pytest.raises(InvestmentReasoningError, match="downstream_decomposition"):
        validate_investment_reasoning_audit(valid_audit(downstream_decomposition=[]))


def test_source_ids_must_be_known_when_allowed_set_is_provided():
    with pytest.raises(InvestmentReasoningError, match="unknown source_signal_ids"):
        validate_investment_reasoning_audit(valid_audit(source_signal_ids=["sig-2"]), allowed_signal_ids={"sig-1"})


def test_public_caveat_rejects_recommendation_language():
    with pytest.raises(InvestmentReasoningError, match="recommendation language"):
        validate_investment_reasoning_audit(valid_audit(public_caveat="建议买入，这是确定性机会。"))
