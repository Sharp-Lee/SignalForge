## MODIFIED Requirements

### Requirement: Pending Signal State
The system SHALL track whether an accepted signal is still pending analysis using one small analysis-state table. A signal is pending when it has no row or has a non-terminal `pending` row in `signal_analysis_state`. Terminal states MUST include `analyzed`, `skipped_stale`, `skipped_failed`, `skipped_weak_logic`, and `skipped_rejected_logic`.

#### Scenario: Newly captured signal is pending
- **WHEN** capture persists a signal and no analysis-state row exists for it
- **THEN** the analyze path treats the signal as pending

#### Scenario: Analyzed signal is not pending
- **WHEN** a signal is marked `analyzed`
- **THEN** later analyze runs MUST NOT analyze it again

#### Scenario: Weak logic signal is not retried
- **WHEN** a signal is marked `skipped_weak_logic`
- **THEN** later analyze runs MUST NOT analyze it again

#### Scenario: Rejected logic signal is not retried
- **WHEN** a signal is marked `skipped_rejected_logic`
- **THEN** later analyze runs MUST NOT analyze it again

## ADDED Requirements

### Requirement: Reasoning Skip Handling
The analyze path SHALL treat weak or rejected investment reasoning as a processed terminal outcome, not a retryable analysis failure. It MUST record an analysis error or status message for observability, mark the selected cluster's signals as `skipped_weak_logic` or `skipped_rejected_logic`, and continue processing other selected clusters.

#### Scenario: Weak logic is skipped without retry
- **WHEN** analysis returns a weak reasoning skip for a selected cluster
- **THEN** the cluster's signals are marked `skipped_weak_logic`
- **AND** no thesis or targets are created for that cluster

#### Scenario: Rejected logic is skipped without retry
- **WHEN** analysis returns a rejected reasoning skip for a selected cluster
- **THEN** the cluster's signals are marked `skipped_rejected_logic`
- **AND** no thesis or targets are created for that cluster
