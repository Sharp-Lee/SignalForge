## 1. Contract Review

- [x] 1.1 Review the `InvestmentReasoningAudit` field set for completeness and minimality.
- [x] 1.2 Confirm `evidence_status` values: `accepted`, `weak`, and `rejected`.
- [x] 1.3 Confirm target-search gating: only accepted audits may allow target search.
- [x] 1.4 Confirm chokepoint candidates remain investigation hints, not recommendations.
- [x] 1.5 Confirm the audit preserves free-form thesis body generation.

## 2. Local Contract Implementation

- [x] 2.1 Add `investment_reasoning` canonical taxonomy constants and audit JSON Schema.
- [x] 2.2 Add fail-closed audit validation for canonical logic, source provenance, target-search gating, and public caveat language.
- [x] 2.3 Add offline tests for valid audit, missing required fields, unknown logic, weak/rejected target gating, missing transmission/decomposition, source provenance, and recommendation language.

## 3. Future Runtime Boundaries

- [x] 3.1 Defer storage decision: future change will choose thesis metadata vs separate table/artifact.
- [x] 3.2 Defer LLM provider prompt/schema wiring to a future change.
- [x] 3.3 Defer analysis orchestration runtime wiring to a future change.
- [x] 3.4 Defer digest rendering for logic chain and public caveat until storage is decided.

## 4. Validation

- [x] 4.1 Run `python -m pytest tests/test_investment_reasoning.py -q`.
- [x] 4.2 Run `python -m pytest tests/ -q`.
- [x] 4.3 Run `openspec validate add-investment-reasoning-skill --strict`.
- [x] 4.4 Return proposal/design/spec/tasks plus implementation summary for review before archive.
