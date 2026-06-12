## ADDED Requirements

### Requirement: Cluster Triage Role
The LLM provider SHALL define a cluster triage role that selects pending signal clusters for deep analysis. The triage prompt MUST ask for Simplified Chinese reasons and MUST judge whether each selected cluster has real tradeable value for an AI ecosystem to A-share research workflow, including hardware, semiconductors, power/energy, data-center infrastructure, cooling, storage, and AI software adoption. The prompt MUST explicitly exclude generic commentary, market chatter, vendor marketing, pure product reviews, duplicate news, and broad technology opinion.

#### Scenario: Triage prompt describes selection criteria
- **WHEN** a triage prompt is built for candidate clusters
- **THEN** it describes AI ecosystem A-share research value, exclusion criteria, and Chinese reason output

### Requirement: Cluster Triage Schema
The LLM provider SHALL define a strict cluster triage output schema with a top-level `selected` array. Each selected item MUST contain `cluster_id` and `reason`, and objects MUST reject additional properties.

#### Scenario: Triage schema contains selected clusters
- **WHEN** the triage schema is inspected
- **THEN** it requires `selected[].cluster_id` and `selected[].reason`

### Requirement: Cluster Triage Enforcement
The LLM provider SHALL enforce that every triage `cluster_id` is a member of the supplied candidate cluster ids. Hallucinated cluster ids, malformed selected items, missing selected arrays, or empty reasons MUST raise `LlmProviderError`. Duplicate selected cluster ids MAY be de-duplicated while preserving first occurrence order.

#### Scenario: Valid triage output is accepted
- **WHEN** triage returns selected cluster ids that are all present in the candidate set with non-empty reasons
- **THEN** enforcement returns the selected items in model order

#### Scenario: Hallucinated cluster id is rejected
- **WHEN** triage returns a cluster id outside the candidate set
- **THEN** enforcement raises `LlmProviderError`

#### Scenario: Empty reason is rejected
- **WHEN** triage returns an empty reason for a selected cluster
- **THEN** enforcement raises `LlmProviderError`
