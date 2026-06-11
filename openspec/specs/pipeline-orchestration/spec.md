# pipeline-orchestration Specification

## Purpose
TBD - created by archiving change add-pipeline-orchestration. Update Purpose after archive.
## Requirements
### Requirement: Composition-only Pipeline

`run_pipeline` MUST compose the existing ingestion, analysis, and target-generation layer functions with an existing `ContractStore`. It MUST NOT reimplement contract validation, analysis assembly, target assembly, or persistence. Operation-layer harnesses MAY choose whether that `ContractStore` is temporary or persistent.

#### Scenario: Pipeline calls existing layer functions
- **WHEN** a pipeline run executes
- **THEN** it uses `run_once`, `analyze`, and `propose_targets` rather than writing layer records directly

#### Scenario: Pipeline writes through ContractStore-backed layers
- **WHEN** pipeline produces theses or targets
- **THEN** those records have passed through their existing `ContractStore` persistence paths

#### Scenario: Live harness injects persistent store
- **WHEN** the live harness is run with a store path
- **THEN** it injects a persistent `ContractStore` into `run_pipeline` without changing pipeline internals

### Requirement: Stage Failure Isolation

Failure in one pipeline unit MUST be recorded in `PipelineResult.errors` and MUST NOT abort the entire pipeline run. Analysis failures MUST be isolated per signal cluster. Target-generation failures MUST be isolated per thesis. Ingestion source failures remain represented by the ingestion result.

#### Scenario: Analysis failure is recorded
- **WHEN** analysis fails for one signal cluster
- **THEN** the pipeline records an analysis-stage error for that cluster and continues processing other clusters

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

This change MUST NOT implement daily/event/weekly scheduling, real provider construction, signal ranking, theme selection, real market data fetching, feedback calibration, LLM-based clustering, or embedding-based clustering.

#### Scenario: Pipeline uses injected providers only
- **WHEN** pipeline is run in tests
- **THEN** adapters, reasoners, proposer, price lookup, and optional clusterer are injected stubs or deterministic local implementations

### Requirement: Clustered Signal Selection

The pipeline MUST support analysis of pending accepted signals, not only signals newly persisted in the current run. Pending signals MUST be clustered before analysis. The live analyze path MUST analyze at most the selected top-K clusters and leave unselected clusters pending. Manual smoke operation MAY still compose capture and analyze in one command, but production scheduling MUST use explicit capture and analyze paths.

#### Scenario: Pending signals are clustered before analysis
- **WHEN** the analyze path runs with pending accepted signals
- **THEN** it passes pending signals through signal clustering before calling analysis

#### Scenario: Only selected clusters are analyzed
- **WHEN** the selector returns fewer clusters than exist in pending
- **THEN** the pipeline calls analysis only for selected clusters

#### Scenario: Unselected clusters are not errors
- **WHEN** a pending cluster is not selected because of the top-K budget
- **THEN** the pipeline does not record an error for that cluster and leaves it pending

#### Scenario: Manual smoke can capture and analyze
- **WHEN** a manual smoke command runs capture and analyze together
- **THEN** it still uses the same pending analysis state and does not rely on a before/after signal diff

