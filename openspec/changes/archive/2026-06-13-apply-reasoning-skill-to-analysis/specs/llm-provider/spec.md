## MODIFIED Requirements

### Requirement: Role Fragment Schemas
The provider MUST use handwritten output schemas that are strict role-fragment subsets of canonical contracts or explicitly local role contracts. The model MUST NOT author orchestration-owned fields such as `track_record`, `review_session`, `status`, target `state`, `priced_in`, linked `thesis_ids`, or target `name`. Target candidate `name` is system-owned reference data stamped from the explicit symbol universe after symbol validation. Investment reasoning output MUST use the canonical `InvestmentReasoningAudit` schema.

Every object in generated schemas MUST set `additionalProperties: false` and MUST list every declared property in `required`. Fields that are truly optional MUST be represented as nullable required fields rather than omitted optional properties.

#### Scenario: Investment reasoning returns audit fragment
- **WHEN** `LlmReasoner.reason("investment_reasoning", context)` is called
- **THEN** it returns an `InvestmentReasoningAudit` fragment validated by the local investment reasoning validator

#### Scenario: Free generation returns thesis fragment
- **WHEN** `LlmReasoner.reason("free_generation", context)` is called
- **THEN** it returns only free-generation fields consumed by analysis orchestration

#### Scenario: Target proposer returns candidate fragment
- **WHEN** `LlmTargetProposer.propose(thesis)` is called
- **THEN** it returns candidate fragments without target `state`, `priced_in`, `thesis_ids`, or model-authored `name`

#### Scenario: Target name is not model-authored
- **WHEN** the target proposal schema is inspected
- **THEN** candidate `name` is not a declared model output field

#### Scenario: Schema drift guard passes
- **WHEN** generated role schemas are compared to canonical contract schema fields and explicitly local role contracts
- **THEN** every emitted field is either allowed by the relevant contract or explicitly orchestration-local

#### Scenario: Generated schemas are all-required
- **WHEN** generated schemas are inspected before a live provider call
- **THEN** every object has `required` equal to its declared `properties`

## ADDED Requirements

### Requirement: Investment Reasoning Provider Enforcement
The provider SHALL enforce investment reasoning role output through the local `InvestmentReasoningAudit` validator. Hallucinated source signal ids, invented logic types, invalid target-search gates, or recommendation language in the public caveat MUST raise `LlmProviderError` and MUST NOT return partial defaults.

#### Scenario: Hallucinated audit provenance is rejected
- **WHEN** investment reasoning output references a source signal id not present in the provided context
- **THEN** the provider raises `LlmProviderError`

#### Scenario: Weak audit cannot allow target search
- **WHEN** investment reasoning output has `evidence_status: weak` and `target_search_decision.status: allowed`
- **THEN** the provider raises `LlmProviderError`
