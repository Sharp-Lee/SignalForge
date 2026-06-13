## ADDED Requirements

### Requirement: Chokepoint-Gated Target Stage
The pipeline target stage SHALL support an optional chokepoint matcher. When a matcher is injected, the pipeline MUST call it after a thesis is confirmed and before target generation. Matched nodes MUST constrain the target universe to their A-share records. No-match or matcher failure MUST skip target generation for that thesis.

#### Scenario: Matched nodes constrain target symbols
- **WHEN** a matcher returns a curated node with two A-share symbols
- **THEN** target generation is called with a symbol universe containing only those symbols

#### Scenario: No match skips target generation
- **WHEN** a matcher returns an empty match list
- **THEN** the pipeline does not call target generation for that thesis

#### Scenario: Matcher failure records error
- **WHEN** a matcher raises during matching
- **THEN** the pipeline records a `chokepoint-match` error
- **AND** target generation is not called for that thesis

#### Scenario: Missing matcher preserves target stage
- **WHEN** no matcher is injected
- **THEN** target generation uses the existing proposer path

### Requirement: Chokepoint Target Metadata
When the chokepoint gate is enabled and targets are produced, each produced target SHOULD carry local metadata identifying the matched chokepoint node and chokepoint holder when the target contract accepts the additional fields. This metadata MUST NOT replace target contract validation.

#### Scenario: Target carries matched node context
- **WHEN** a target is produced from a matched chokepoint node
- **THEN** the returned target includes the matched node name and chokepoint holder as local context
