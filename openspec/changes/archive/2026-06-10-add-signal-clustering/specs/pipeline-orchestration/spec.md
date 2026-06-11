## ADDED Requirements

### Requirement: Clustered Signal Selection

The pipeline MUST cluster newly persisted signals from the current run before analysis. It MUST call an injected signal clusterer when provided and MUST use the default deterministic clusterer otherwise. Each returned cluster MUST be analyzed independently, producing zero or one thesis per successful cluster. Clustering, not the analysis prompt, owns pre-analysis grouping.

#### Scenario: Newly persisted signals are clustered before analysis
- **WHEN** ingestion persists multiple new signals during the current run
- **THEN** the pipeline passes those signals through signal clustering before calling analysis

#### Scenario: Each cluster is analyzed independently
- **WHEN** the clusterer returns multiple clusters
- **THEN** the pipeline calls analysis separately for each cluster and may return multiple theses

#### Scenario: Singleton clusters are analyzed
- **WHEN** a new signal has no related signals in the current batch
- **THEN** the pipeline analyzes it as a one-signal cluster

## MODIFIED Requirements

### Requirement: Stage Failure Isolation

Failure in one pipeline unit MUST be recorded in `PipelineResult.errors` and MUST NOT abort the entire pipeline run. Analysis failures MUST be isolated per signal cluster. Target-generation failures MUST be isolated per thesis. Ingestion source failures remain represented by the ingestion result.

#### Scenario: Analysis failure is recorded
- **WHEN** analysis fails for one signal cluster
- **THEN** the pipeline records an analysis-stage error for that cluster and continues processing other clusters

#### Scenario: Target generation failure is recorded
- **WHEN** target generation fails for one thesis
- **THEN** the pipeline records a target-stage error and continues returning any successful theses or targets

### Requirement: MVP Boundaries

This change MUST NOT implement daily/event/weekly scheduling, real provider construction, signal ranking, theme selection, real market data fetching, feedback calibration, LLM-based clustering, or embedding-based clustering.

#### Scenario: Pipeline uses injected providers only
- **WHEN** pipeline is run in tests
- **THEN** adapters, reasoners, proposer, price lookup, and optional clusterer are injected stubs or deterministic local implementations

## REMOVED Requirements

### Requirement: Trivial Signal Selection Boundary

**Reason**: The trivial single-group boundary produced incoherent theses once real dedup began preserving multiple distinct RSS signals.

**Migration**: Use `Clustered Signal Selection`; newly persisted signals are grouped by the signal clusterer before analysis.
