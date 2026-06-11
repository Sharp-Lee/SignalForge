## Context

The system has separate callable layers for ingestion (`source_ingestion.runner.run_once`), analysis (`analysis_orchestration.analyze`), and target generation (`target_generation.propose_targets`). Each layer already uses `ContractStore` and canonical contracts for validation and persistence. What is missing is a single orchestration entrypoint that composes those layers into one offline-testable pipeline run.

This change adds that composition layer only. It does not change layer contracts, does not add provider integrations, and does not implement scheduling policy.

## Goals / Non-Goals

**Goals:**
- Add `run_pipeline(...) -> PipelineResult` as a thin coordinator.
- Compose existing ingestion, analysis, and target generation functions.
- Use trivial signal grouping from signals newly persisted during the current run.
- Record per-stage errors without aborting the whole pipeline.
- Aggregate ingestion counts, thesis outputs, watchlist targets, empty recommendations, and errors.

**Non-Goals:**
- No daily/event/weekly scheduler.
- No signal clustering, ranking, or selection strategy.
- No real LLM, market data, or source provider wiring.
- No feedback calibration.
- No replacement of existing contract validation or persistence logic.

## Decisions

**D1 Pipeline is composition-only.** `run_pipeline` calls `run_once`, `analyze`, and `propose_targets`. It does not reimplement signal validation, thesis assembly, target assembly, or storage writes.

**D2 Trivial signal selection uses newly persisted signals.** The pipeline snapshots signal ids before ingestion, runs `run_once`, then reads signals whose ids were not present before the run. In this MVP all newly persisted signals form one group. Clustering and theme selection are explicitly deferred.

**D3 Stage failures are isolated at the pipeline boundary.** Ingestion already records source-level failures. The pipeline catches analysis failures per signal group and target-generation failures per thesis, records them in `PipelineResult.errors`, and continues with other units.

**D4 Provider seams pass through unchanged.** Adapters, author/reviewer reasoners, target proposer, and price lookup are all injected into `run_pipeline` and passed to their layer functions. The pipeline does not construct real providers.

**D5 Empty recommendations are first-class results.** When target generation returns an empty recommendation, the pipeline records it instead of treating it as an error. This preserves the "no opportunity is a valid output" discipline.

## Risks / Trade-offs

- Reading newly persisted signals from storage is a small storage coupling. -> Keep it read-only and limit it to selecting current-run ids; all writes still go through existing layer functions.
- One trivial group can mix unrelated signals. -> This is an MVP boundary, documented and tested; clustering is a later change.
- Continuing after failures can hide broken stages. -> Aggregate all errors in `PipelineResult` so the caller can inspect partial success and failures together.
- Duplicate signal rejection may produce no new signals. -> Return a completed pipeline result with no thesis and no forced target.

## Migration Plan

1. Add `pipeline-orchestration` delta spec and tasks.
2. Implement `PipelineResult`, trivial signal selection, and `run_pipeline`.
3. Add offline end-to-end, analysis-failure, target-failure, and empty-recommendation tests.
4. Validate with `openspec validate add-pipeline-orchestration --strict` and `python3 -m pytest -q`.

## Open Questions

- Real scheduling semantics for daily/event/weekly runs are deferred.
- Signal grouping and ranking strategy are deferred.
- Provider construction and configuration are deferred.
