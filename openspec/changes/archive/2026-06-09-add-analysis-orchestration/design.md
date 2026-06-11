## Context

The ingestion layer can persist validated signals into the SQLite memory base, and `thesis-contract` already defines the shape and semantic gates for confirmed theses. What is still missing is the analysis orchestration layer: a small, testable component that turns selected signals into a confirmed thesis by running the required reasoning steps and then handing the assembled record to `ContractStore.add_thesis()`.

This change builds the orchestration skeleton only. Real LLM providers, signal selection, clustering, target generation, and feedback calibration remain separate changes.

## Goals / Non-Goals

**Goals:**
- Define a `Reasoner` protocol whose LLM I/O is injectable.
- Run the thesis flow as free generation -> completeness critique -> adversarial falsification -> assembly -> `ContractStore.add_thesis()`.
- Enforce author/reviewer independence through separate reasoner metadata before attempting confirmation.
- Keep tests offline with deterministic reasoner stubs.
- Reuse `thesis-contract` validation and storage instead of duplicating thesis invariants.

**Non-Goals:**
- No production LLM provider.
- No signal clustering, ranking, or selection strategy.
- No target generation.
- No feedback calibration engine.
- No automatic extraction of complex cross-market transmission paths beyond fields explicitly returned by the injected reasoner.

## Decisions

**D1 Reasoner is a protocol, not a provider.** The orchestration layer calls `reasoner.reason(role, context)` and receives structured output. Production LLM providers can later wrap this protocol, but this change ships only stubs and protocol types. This keeps tests offline and avoids coupling the orchestration contract to any model SDK.

**D2 Roles are explicit and narrow.** The author reasoner is invoked with `free_generation`, then `completeness_critique`; the reviewer reasoner is invoked with `adversarial_falsification`. The orchestration layer does not ask the model to produce a complete database record. It assembles only the known contract fields from role outputs.

**D3 Independence is checked before storage.** The orchestrator requires `author.instance_id != reviewer.instance_id` and `author.persona != reviewer.persona`. `thesis-contract` still performs the final semantic gate during `ContractStore.add_thesis()`, but the orchestration layer must not knowingly construct a self-reviewed thesis.

**D4 Completeness critique is an audit object.** The critique step records notes, candidate thesis ids, and `body_unchanged=True`. It may identify missing second-order effects, but it must not rewrite the free-form body or force a reasoning template.

**D5 Persistence goes through `ContractStore`.** `analyze()` returns the stored thesis id and validated record after calling `ContractStore.add_thesis()`. The orchestrator never writes directly to SQLite and never bypasses schema or semantic validation.

**D6 Track record defaults are explicit orchestration inputs.** The reasoner may return direction, falsifiable expectation, and verification window. If omitted, the orchestrator uses conservative defaults supplied by the caller. This keeps the MVP usable while preserving a visible falsifiable record.

## Risks / Trade-offs

- Reasoner output may be malformed. -> Fail fast with a contract/orchestration error before persistence, and cover malformed steps in tests.
- Stubs can hide real LLM behavior. -> Keep the protocol narrow, require structured role outputs, and defer real provider integration to a dedicated change with recorded fixtures.
- The orchestrator could start duplicating thesis validation. -> Only precheck role independence and required role outputs; final invariants remain in `ContractStore.add_thesis()`.
- Confirmed theses may be too easy to produce from weak signals. -> Existing `thesis-contract` labels single-source and no-source uncertainty; signal selection quality is left to a later analysis-selection change.

## Migration Plan

1. Add `analysis-orchestration` delta spec and tasks.
2. Implement reasoner protocol, deterministic stub, and orchestration entrypoint.
3. Add offline regression tests for the full three-step flow and failure gates.
4. Validate with `openspec validate add-analysis-orchestration --strict` and `python3 -m pytest -q`.

## Open Questions

- Production prompt design and LLM provider selection are deferred.
- Signal selection and grouping for weekly versus event-driven analysis are deferred.
- Rich cross-market transmission extraction is deferred beyond fields explicitly returned by reasoner stubs.
