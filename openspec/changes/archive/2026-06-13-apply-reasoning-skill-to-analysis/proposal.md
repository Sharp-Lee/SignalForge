## Why

The investment reasoning audit now exists as a local contract, but live analysis still jumps directly from signal cluster to free-form thesis. To fully realize the user's workflow, analysis must first decide whether the signal contains accepted investment logic; weak or rejected logic should stop cleanly instead of creating a thesis or retrying forever.

## What Changes

- Add an investment-reasoning role to the LLM provider boundary, using the existing `InvestmentReasoningAudit` schema and validator.
- Update analysis orchestration so `analyze()` runs investment reasoning before free thesis generation.
- Preserve free-form thesis body generation: accepted reasoning is context/audit metadata, not a fixed thesis template.
- Gate analysis: accepted audits continue into the existing free-generation -> completeness critique -> adversarial review flow; weak/rejected audits raise a typed non-actionable result.
- Update pending analysis handling so weak/rejected logic is marked terminal (`skipped_weak_logic` / `skipped_rejected_logic`) rather than retried as failures.
- Keep target generation unchanged; it only runs when analysis successfully produces a confirmed thesis.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `investment-reasoning-skill`: Apply the audit as a runtime analysis gate while preserving free-form thesis reasoning.
- `llm-provider`: Add an investment reasoning role schema, prompt, and enforcement.
- `analysis-orchestration`: Run the investment reasoning audit before thesis generation and return it with successful analysis.
- `capture-analyze-flow`: Treat weak/rejected reasoning as terminal skip states rather than retryable analysis failures.

## Impact

- Affected modules: `llm_provider`, `analysis_orchestration`, `pipeline_orchestration`, tests, and OpenSpec specs.
- No market data, target assembly, target contract, chokepoint map data, source ingestion, scheduling, or digest behavior is changed in this step.
- Default tests remain offline with stub reasoners/transports.
