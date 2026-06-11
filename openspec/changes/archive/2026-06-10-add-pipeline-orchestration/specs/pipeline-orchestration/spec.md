## ADDED Requirements

### Requirement: Composition-only Pipeline

`run_pipeline` MUST compose the existing ingestion, analysis, and target-generation layer functions with an existing `ContractStore`. It MUST NOT reimplement contract validation, analysis assembly, target assembly, or persistence.

#### Scenario: Pipeline calls existing layer functions
- **WHEN** a pipeline run executes
- **THEN** it uses `run_once`, `analyze`, and `propose_targets` rather than writing layer records directly

#### Scenario: Pipeline writes through ContractStore-backed layers
- **WHEN** pipeline produces theses or targets
- **THEN** those records have passed through their existing `ContractStore` persistence paths

### Requirement: Trivial Signal Selection Boundary

The pipeline MUST use only trivial signal selection in this change. It MUST group newly persisted signals from the current run into a simple analysis group. Signal clustering, ranking, theme selection, and scheduling policy MUST remain out of scope.

#### Scenario: Newly persisted signals form a group
- **WHEN** ingestion persists one or more new signals during the current run
- **THEN** the pipeline forms a trivial analysis group from those signals

#### Scenario: No clustering strategy is applied
- **WHEN** multiple unrelated signals are persisted
- **THEN** the pipeline does not attempt semantic clustering or ranking in this change

### Requirement: Stage Failure Isolation

Failure in one pipeline unit MUST be recorded in `PipelineResult.errors` and MUST NOT abort the entire pipeline run. Analysis failures MUST be isolated per signal group. Target-generation failures MUST be isolated per thesis. Ingestion source failures remain represented by the ingestion result.

#### Scenario: Analysis failure is recorded
- **WHEN** analysis fails for a signal group
- **THEN** the pipeline records an analysis-stage error and continues to return the ingestion result

#### Scenario: Target generation failure is recorded
- **WHEN** target generation fails for one thesis
- **THEN** the pipeline records a target-stage error and continues returning any successful theses or targets

### Requirement: Contracted Outputs

Pipeline-produced theses and targets MUST still satisfy their canonical contracts through existing layer calls. The pipeline MUST NOT bypass `thesis-contract` or `target-contract` checks.

#### Scenario: Thesis output is contract validated
- **WHEN** pipeline analysis produces a thesis
- **THEN** the thesis has been persisted by the analysis layer through `ContractStore.add_thesis()`

#### Scenario: Target output is contract validated
- **WHEN** pipeline target generation produces a target
- **THEN** the target has been persisted by target generation through `ContractStore.add_target()`

### Requirement: Empty Recommendation Propagation

When target generation returns an empty recommendation, the pipeline MUST include it in `PipelineResult.empty_recommendations` and MUST NOT treat it as a failure.

#### Scenario: Empty recommendation is preserved
- **WHEN** no target qualifies for a generated thesis
- **THEN** the pipeline returns the empty recommendation with its reasons

### Requirement: MVP Boundaries

This change MUST NOT implement daily/event/weekly scheduling, real provider construction, signal clustering, real market data fetching, or feedback calibration.

#### Scenario: Pipeline uses injected providers only
- **WHEN** pipeline is run in tests
- **THEN** adapters, reasoners, proposer, and price lookup are injected stubs
