## MODIFIED Requirements

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
