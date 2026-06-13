## ADDED Requirements

### Requirement: Chokepoint Matcher Role
The LLM provider SHALL define a chokepoint matcher role that judges whether a confirmed thesis is a real catalyst for any supplied curated chokepoint node. The prompt MUST instruct the model to match only when the thesis can materially affect the node's supply, demand, price, capacity, or orders. The prompt MUST default to no match for shallow mentions, generic product news, or loosely related topics. Reasons MUST be written in Simplified Chinese.

#### Scenario: Matcher prompt describes true catalyst criteria
- **WHEN** a chokepoint matcher prompt is built
- **THEN** it tells the model to match only true chokepoint catalysts, reject shallow mentions, and write Chinese reasons

### Requirement: Chokepoint Matcher Schema
The LLM provider SHALL define a strict chokepoint matcher output schema with a top-level `matched` array. Each matched item MUST contain `node` and `reason`, and objects MUST reject additional properties.

#### Scenario: Matcher schema contains node matches
- **WHEN** the matcher schema is inspected
- **THEN** it requires `matched[].node` and `matched[].reason`

### Requirement: Chokepoint Matcher Enforcement
The LLM provider SHALL enforce that every returned `node` is a member of the supplied allowed node names. Hallucinated node names, malformed matched items, missing matched arrays, or empty reasons MUST raise `LlmProviderError`. Duplicate matched nodes MAY be de-duplicated while preserving first occurrence order.

#### Scenario: Valid matcher output is accepted
- **WHEN** matcher output contains only allowed node names with non-empty reasons
- **THEN** enforcement returns matched items in model order

#### Scenario: Hallucinated node is rejected
- **WHEN** matcher output contains a node outside the supplied allowed node names
- **THEN** enforcement raises `LlmProviderError`

#### Scenario: Empty reason is rejected
- **WHEN** matcher output contains an empty reason for a matched node
- **THEN** enforcement raises `LlmProviderError`
