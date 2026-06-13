## ADDED Requirements

### Requirement: Chokepoint Relevance Gate
The system SHALL support an optional chokepoint relevance gate between confirmed thesis generation and target generation. When enabled, a thesis MUST match at least one curated, screen-passing chokepoint node before target generation is attempted. When no nodes match, the pipeline MUST produce no targets for that thesis and MUST NOT treat the no-target outcome as a target-generation failure.

#### Scenario: Matched node allows target generation
- **WHEN** a confirmed thesis matches one curated chokepoint node
- **THEN** target generation is attempted only with A-share symbols attached to that matched node

#### Scenario: No matched node suppresses targets
- **WHEN** a confirmed thesis matches no curated chokepoint node
- **THEN** the pipeline skips target generation for that thesis
- **AND** no target is produced from the full universe

### Requirement: Fail-Closed Matcher Discipline
The chokepoint relevance gate MUST fail closed. If matcher invocation raises, times out, or returns structurally invalid output, the pipeline MUST record an error for that thesis and MUST skip target generation. It MUST NOT fall back to all-universe target generation.

#### Scenario: Matcher failure skips target generation
- **WHEN** the chokepoint matcher raises for a thesis
- **THEN** the pipeline records a `chokepoint-match` error
- **AND** target generation is skipped for that thesis

### Requirement: Backward Compatible Injection
The chokepoint relevance gate MUST be injectable. When no matcher is injected, existing target-generation behavior MUST remain unchanged and the pipeline MAY continue using the original proposer and symbol universe.

#### Scenario: Missing matcher preserves legacy behavior
- **WHEN** `matcher = None`
- **THEN** a confirmed thesis proceeds to target generation through the existing path
