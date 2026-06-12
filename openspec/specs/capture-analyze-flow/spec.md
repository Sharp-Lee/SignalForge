# capture-analyze-flow Specification

## Purpose
TBD - created by archiving change decouple-capture-analyze. Update Purpose after archive.
## Requirements
### Requirement: Capture Path Persists Signals Only

The system SHALL provide a capture path that runs configured source adapters and persists accepted signals through the existing ingestion runner without invoking signal clustering, LLM analysis, target generation, market data lookup, or digest generation.

#### Scenario: Capture does not analyze
- **WHEN** the capture path runs with adapters and a store
- **THEN** it writes accepted signals through the existing contracted ingestion path and returns ingestion counts only

### Requirement: Pending Signal State

The system SHALL track whether an accepted signal is still pending analysis using one small analysis-state table. A signal is pending when it has no row or has a non-terminal `pending` row in `signal_analysis_state`. Terminal states MUST be `analyzed`, `skipped_stale`, and `skipped_failed`.

#### Scenario: Newly captured signal is pending
- **WHEN** capture persists a signal and no analysis-state row exists for it
- **THEN** the analyze path treats the signal as pending

#### Scenario: Analyzed signal is not pending
- **WHEN** a signal is marked `analyzed`
- **THEN** later analyze runs MUST NOT analyze it again

### Requirement: Pending Analysis Reads Store State

The analyze path SHALL read pending signals from the persistent store rather than relying on a before/after current-run signal diff. Capture that succeeds before a crash MUST leave signals available for a later analyze run.

#### Scenario: Capture crash recovery
- **WHEN** capture persists signals and the process exits before analysis
- **THEN** a later analyze run against the same store reads those signals as pending

### Requirement: Budgeted Top-K Analysis

The analyze path SHALL cluster pending signals with the existing deterministic signal clusterer and analyze at most `top_k` clusters in a run. Unselected clusters MUST remain pending and MUST NOT be treated as errors.

#### Scenario: Top-K cap is enforced
- **WHEN** more pending clusters exist than `top_k`
- **THEN** only `top_k` clusters are analyzed and the rest remain pending

#### Scenario: Unselected pending is retained
- **WHEN** a cluster is not selected because of the top-K budget
- **THEN** its signals have no terminal analysis-state row after the run

### Requirement: Stale Pending Expiry

The analyze path SHALL mark pending signals older than a configurable `pending_max_age_days` window as `skipped_stale` before clustering. Stale signals MUST NOT be analyzed.

#### Scenario: Old pending signal is skipped stale
- **WHEN** a pending signal published before the stale cutoff is encountered
- **THEN** it is marked `skipped_stale` and excluded from cluster selection

### Requirement: Failed Cluster Attempt Cap

The analyze path SHALL increment attempts for signals in a selected cluster when analysis fails. When a selected cluster reaches the configured `max_attempts`, those signals MUST be marked `skipped_failed` and no longer retried.

#### Scenario: Failed cluster is retried below cap
- **WHEN** analysis fails for a selected cluster below the attempt cap
- **THEN** its signals remain pending with incremented attempts

#### Scenario: Failed cluster reaches cap
- **WHEN** analysis fails for a selected cluster at the attempt cap
- **THEN** its signals are marked `skipped_failed` and later analyze runs skip them

### Requirement: Existing Analysis And Target Layers Remain Canonical

The analyze path SHALL call existing `analyze()` and `propose_targets()` functions for selected clusters and MUST NOT reimplement thesis assembly, target assembly, LLM prompts, contract validation, or persistence.

#### Scenario: Selected cluster uses existing layers
- **WHEN** a selected cluster is processed
- **THEN** thesis and target outputs are produced only through existing analysis and target-generation layer functions

### Requirement: AI Ecosystem Signal Priority Hints
The analyze path's cheap cluster scoring SHALL recognize AI ecosystem infrastructure terms beyond semiconductor/server hardware, including power, energy, data-center, cooling, grid, utility, storage, and AI software/adoption terms. These hints MUST remain deterministic input-side prioritization and MUST NOT replace LLM thesis reasoning.

#### Scenario: Energy infrastructure signal receives priority hint
- **WHEN** a pending signal mentions data-center power, grid, utility, cooling, storage, solar, or megawatt terms
- **THEN** cheap cluster scoring treats it as relevant AI ecosystem infrastructure

#### Scenario: Software adoption signal receives priority hint
- **WHEN** a pending signal mentions AI agents, inference, enterprise AI, or AI software adoption
- **THEN** cheap cluster scoring treats it as relevant AI ecosystem context

### Requirement: LLM Cluster Triage Selection
The analyze path SHALL support optional LLM cluster triage after deterministic clustering and before deep analysis. When a triage selector is configured, the analyze path MUST use the triage-selected clusters for analysis. When no triage selector is configured, existing keyword top-K selection MUST remain the default behavior.

#### Scenario: Triage selector chooses clusters
- **WHEN** pending signals are clustered and a triage selector returns valid selected cluster ids
- **THEN** the analyze path processes those clusters rather than direct keyword top-K output

#### Scenario: No triage selector preserves existing selection
- **WHEN** no triage selector is configured
- **THEN** the analyze path uses the existing keyword top-K selector

### Requirement: Freshness-Bounded Triage Candidates
The analyze path SHALL bound triage prompt size with a configurable `triage_candidate_limit`. When the number of pending clusters exceeds that limit, candidates supplied to triage MUST be the newest clusters by maximum source `published_at`. Candidate limiting MUST NOT use keyword score or other value judgment before triage.

#### Scenario: Candidate limit uses newest clusters
- **WHEN** pending cluster count exceeds `triage_candidate_limit`
- **THEN** only the newest clusters by source published time are supplied to triage

#### Scenario: Candidate limit does not use keyword score
- **WHEN** pending cluster count exceeds `triage_candidate_limit`
- **THEN** keyword score is not used to decide which clusters are supplied to triage

### Requirement: Triage Fallback
The analyze path SHALL fall back to the existing keyword top-K selector when triage raises an error, returns invalid output, returns hallucinated cluster ids, or returns an empty selection. Cluster selection MUST NOT fail the entire analyze run.

#### Scenario: Triage error falls back
- **WHEN** the triage selector raises an error
- **THEN** the analyze path selects clusters through the existing keyword top-K selector and continues

#### Scenario: Empty triage output falls back
- **WHEN** the triage selector returns no selected clusters
- **THEN** the analyze path selects clusters through the existing keyword top-K selector and continues

### Requirement: Triage Reason Persistence
The analyze path SHALL persist the triage selection reason for signals in selected clusters. Triage reasons MUST be stored in operation state such as `signal_analysis_state` and MUST NOT be added to thesis-contract or target-contract objects.

#### Scenario: Selected cluster reason is stored
- **WHEN** triage selects a cluster with a reason and the analyze path processes that cluster
- **THEN** each signal in that selected cluster has the triage reason recorded in analysis state

#### Scenario: Contract objects are unchanged
- **WHEN** triage reasons are recorded
- **THEN** thesis and target contract payloads are not modified to include triage-only fields

