## ADDED Requirements

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
