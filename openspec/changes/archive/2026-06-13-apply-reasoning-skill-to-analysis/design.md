## Context

The system has three relevant layers:

- `investment-logic-taxonomy`: canonical logic types and boundary rules.
- `investment_reasoning`: local schema and fail-closed validator for an `InvestmentReasoningAudit`.
- `analysis_orchestration.analyze()`: currently creates a confirmed thesis from selected signals through free generation, completeness critique, and adversarial falsification.

The missing runtime step is applying the audit before free-form thesis generation. The goal is not to make the thesis rigid. The goal is to prevent weak news from flowing into target generation and to record the logic gate when a thesis is produced.

## Goals / Non-Goals

**Goals:**

- Add an investment reasoning LLM role with injectable/offline-testable transport.
- Run the audit before free generation in `analyze()`.
- Return the audit in `AnalysisResult` for downstream callers.
- For accepted audits, continue through existing thesis generation and target generation.
- For weak/rejected audits, stop as a non-actionable analysis result and mark signals terminal in pending analysis.
- Preserve free-form thesis body and existing completeness/adversarial gates.

**Non-Goals:**

- Do not alter target generation internals.
- Do not add map-assisted target selection yet.
- Do not render audit fields in digest yet.
- Do not change chokepoint map schema/data.
- Do not call real LLMs in tests.

## Decisions

### D1. Audit runs before free generation

`analyze()` should call `author_reasoner.reason("investment_reasoning", base_context)` before `free_generation`.

If the audit is accepted, `free_generation` receives it in context so the model can use the audit while preserving free prose. If the audit is weak or rejected, `analyze()` raises a typed `AnalysisSkipped` result and does not call free generation, completeness critique, adversarial review, or `ContractStore.add_thesis()`.

Rationale: the audit is the gate. Running it after thesis generation would waste tokens and allow weak signals to look like confirmed theses.

### D2. Weak/rejected is not an error retry

Weak/rejected reasoning means the signal was processed and intentionally skipped. Pending analysis should mark the cluster terminal:

- `skipped_weak_logic`
- `skipped_rejected_logic`

These states are not retryable failures and should not consume future top-K slots.

Rationale: otherwise weak news becomes an infinite retry loop.

### D3. AnalysisResult carries the audit

For accepted audits, `AnalysisResult` should include `investment_reasoning`. The thesis payload may also include it because `thesis-contract` currently accepts additional metadata, but callers should not rely on it as part of the thesis body.

Rationale: downstream target generation and digest can be upgraded later without re-running the LLM audit.

### D4. LLM provider role uses existing audit schema

`llm_provider.schemas` should expose `INVESTMENT_REASONING_SCHEMA` by importing or referencing the canonical `INVESTMENT_REASONING_AUDIT_SCHEMA`. `LlmReasoner` should support role `investment_reasoning`, use a dedicated system prompt, and enforce output through `validate_investment_reasoning_audit()`.

Rationale: one schema source prevents drift between local validator and provider role.

### D5. Target generation remains unchanged

The pipeline already calls `propose_targets()` only after `analyze()` succeeds. Once weak/rejected audits skip analysis, target generation is naturally gated without changing target logic.

## Risks / Trade-offs

- [Audit adds one LLM call per selected cluster] -> It is cheaper than full thesis generation and prevents weak clusters from continuing.
- [Weak but interesting signals are hidden] -> Store terminal state separately as `skipped_weak_logic`; future digest can show them as watch-only if desired.
- [Audit constrains thesis prose too much] -> Pass audit as context only; do not force body fields.
- [Existing tests with stub reasoners break] -> Update stubs to provide `investment_reasoning` or use helper defaults.
- [Storing audit inside thesis is too implicit] -> Treat it as metadata for now; a later storage change can normalize it if needed.

## Migration Plan

1. Add provider schema/prompt/enforcement for `investment_reasoning`.
2. Update `analysis_orchestration.analyze()` to run audit first and return/store it for accepted audits.
3. Add `AnalysisSkipped` for weak/rejected audits.
4. Update `pipeline_orchestration.analyze_pending()` to mark weak/rejected clusters as terminal skip states.
5. Update offline tests for accepted, weak, rejected, invalid audit, and pipeline terminal-state behavior.
6. Run full tests and OpenSpec validation.
