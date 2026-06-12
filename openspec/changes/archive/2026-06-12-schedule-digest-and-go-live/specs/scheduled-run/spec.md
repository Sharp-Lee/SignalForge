## MODIFIED Requirements

### Requirement: Self-contained Scheduled Wrapper

The system SHALL provide scheduled-run wrappers or modes that execute capture and analyze independently without relying on an interactive shell environment. Capture MUST source runtime configuration and run configured feeds frequently. Analyze MUST source runtime configuration, run the pending analyze path against the persistent store, and generate the daily digest after analysis succeeds. Pipeline mode MUST also generate the daily digest after the combined pipeline succeeds. Capture mode MUST NOT generate a digest.

#### Scenario: Capture wrapper runs without analysis
- **WHEN** the scheduled capture command runs
- **THEN** it persists accepted signals and exits without invoking LLM analysis, target generation, or digest generation

#### Scenario: Analyze wrapper processes pending and writes digest
- **WHEN** the scheduled analyze command runs and exits successfully
- **THEN** it analyzes pending signals up to the configured top-K budget
- **AND** it generates the daily Markdown and HTML digest for the persistent store using the UTC date that matches stored `track_record.created_at`
- **AND** the scheduled log includes the generated digest paths

#### Scenario: Failed analysis does not write digest
- **WHEN** the scheduled analyze command exits non-zero
- **THEN** digest generation is skipped
- **AND** the scheduled log records the non-zero exit code

#### Scenario: Pipeline wrapper writes digest after success
- **WHEN** the scheduled pipeline command runs and exits successfully
- **THEN** it generates the daily Markdown and HTML digest for the persistent store
