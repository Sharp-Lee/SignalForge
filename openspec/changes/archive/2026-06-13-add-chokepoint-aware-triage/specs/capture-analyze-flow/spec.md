## MODIFIED Requirements

### Requirement: LLM Cluster Triage Selection
The analyze path SHALL support optional LLM cluster triage after deterministic clustering and before deep analysis. When a triage selector is configured, the analyze path MUST use the triage-selected clusters for analysis. When no triage selector is configured, existing keyword top-K selection MUST remain the default behavior.

When a configured triage selector supports a `chokepoint_nodes` parameter, the analyze path MUST pass the compact curated, screen-passing chokepoint nodes from the chokepoint map into that selector. This context MUST be used only as a soft prioritization aid for cluster selection. It MUST NOT hard-filter unmatched clusters and MUST NOT replace the target-stage chokepoint relevance gate. Selectors that do not support `chokepoint_nodes` MUST continue to work with the previous call shape.

#### Scenario: Triage selector chooses clusters
- **WHEN** pending signals are clustered and a triage selector returns valid selected cluster ids
- **THEN** the analyze path processes those clusters rather than direct keyword top-K output

#### Scenario: No triage selector preserves existing selection
- **WHEN** no triage selector is configured
- **THEN** the analyze path uses the existing keyword top-K selector

#### Scenario: Compatible triage selector receives chokepoint nodes
- **WHEN** a triage selector accepts `chokepoint_nodes` and curated screen-passing nodes exist
- **THEN** the analyze path supplies those nodes to the selector for soft prioritization

#### Scenario: Legacy triage selector remains compatible
- **WHEN** a triage selector does not accept `chokepoint_nodes`
- **THEN** the analyze path calls it with the previous triage arguments and continues normally

#### Scenario: Chokepoint-aware triage remains soft
- **WHEN** a cluster does not match a supplied chokepoint node at triage time
- **THEN** the triage layer MUST NOT hard-delete the cluster solely for being unmatched
