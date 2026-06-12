## 1. Contract Review

- [ ] 1.1 Review the `InvestmentReasoningAudit` field set for completeness and minimality.
- [ ] 1.2 Confirm `evidence_status` values: `accepted`, `weak`, and `rejected`.
- [ ] 1.3 Confirm target-search gating: only accepted audits may allow target search.
- [ ] 1.4 Confirm chokepoint candidates remain investigation hints, not recommendations.
- [ ] 1.5 Confirm the audit preserves free-form thesis body generation.

## 2. Future Implementation Plan

- [ ] 2.1 Decide whether the audit will be stored inside thesis metadata or in a separate table/artifact.
- [ ] 2.2 Add a future LLM provider schema and enforcement for the audit shape.
- [ ] 2.3 Add future analysis orchestration wiring that produces the audit before final thesis assembly.
- [ ] 2.4 Add tests that weak/rejected audits do not proceed into target search.
- [ ] 2.5 Add future digest rendering for logic chain and public caveat after storage is decided.

## 3. Validation

- [ ] 3.1 Run `openspec validate add-investment-reasoning-skill --strict`.
- [ ] 3.2 Return proposal/design/spec/tasks for review before implementation or archive.
