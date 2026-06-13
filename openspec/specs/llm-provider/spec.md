# llm-provider Specification

## Purpose
TBD - created by archiving change add-llm-provider. Update Purpose after archive.
## Requirements
### Requirement: Injectable Claude Transport

The LLM provider MUST isolate SDK and network access behind an injectable `Completion` transport. The default Anthropic transport MUST lazily construct its client only at first real call, read the API key from `ANTHROPIC_API_KEY`, use model `claude-opus-4-8`, and call `messages.create` with JSON-schema structured output through `output_config.format`.

#### Scenario: Lazy client construction
- **WHEN** `LlmReasoner`, `LlmTargetProposer`, or `AnthropicCompletion` is imported or constructed without an API key
- **THEN** no Anthropic client is created and no network call is attempted

#### Scenario: Structured output request
- **WHEN** a real Claude completion is invoked
- **THEN** the transport sends `system`, `user`, a generated JSON schema, `max_tokens`, and the role's thinking setting to `messages.create`

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

### Requirement: Investment Reasoning Provider Enforcement
The provider SHALL enforce investment reasoning role output through the local `InvestmentReasoningAudit` validator. Hallucinated source signal ids, invented logic types, invalid target-search gates, or recommendation language in the public caveat MUST raise `LlmProviderError` and MUST NOT return partial defaults.

#### Scenario: Hallucinated audit provenance is rejected
- **WHEN** investment reasoning output references a source signal id not present in the provided context
- **THEN** the provider raises `LlmProviderError`

#### Scenario: Weak audit cannot allow target search
- **WHEN** investment reasoning output has `evidence_status: weak` and `target_search_decision.status: allowed`
- **THEN** the provider raises `LlmProviderError`

### Requirement: Provenance And Symbol Enforcement

The provider MUST reject hallucinated provenance and invalid symbols. Every model-produced `source_signal_ids` array MUST be a subset of the provided signal ids. `LlmTargetProposer` MUST fail closed unless an explicit authoritative `symbol_universe` mapping is provided. Every proposed target symbol MUST be a key in that universe. Candidate `name` MUST be stamped from the universe mapping after symbol validation and MUST NOT be trusted from model output.

#### Scenario: Hallucinated signal id is rejected
- **WHEN** Claude returns a `source_signal_ids` value not present in `PROVIDED_SIGNAL_IDS`
- **THEN** the provider raises `LlmProviderError` and returns no partial role output

#### Scenario: Out-of-universe symbol is rejected
- **WHEN** a target candidate symbol is outside the configured symbol universe
- **THEN** the provider raises `LlmProviderError` and returns no candidates

#### Scenario: Missing symbol universe is rejected before target generation
- **WHEN** `LlmTargetProposer.propose()` is called without a `symbol_universe`
- **THEN** the provider raises `LlmProviderError` before calling transport or storing targets

#### Scenario: Candidate name is stamped from universe
- **WHEN** a target candidate symbol is present in the authoritative universe mapping
- **THEN** the provider sets candidate `name` to the mapped authoritative company name before target generation assembles a target

#### Scenario: Empty catalysts are not provider structural errors
- **WHEN** a target candidate has an empty `catalysts` or `exit_triggers` array
- **THEN** the provider returns the candidate for target generation to reject with a per-candidate reason

#### Scenario: Damaged catalyst structure is rejected
- **WHEN** a target candidate has a catalyst or exit trigger element without a non-empty `description`
- **THEN** the provider raises `LlmProviderError` and returns no candidates

### Requirement: Provider Error Discipline

All provider failures MUST raise `LlmProviderError` and MUST NOT return partial defaults. This includes Anthropic API errors, stop reasons `refusal` or `max_tokens`, missing text blocks, invalid JSON, unknown roles, missing required role fields, missing or invalid `direction`, `confidence`, or `verification_window`, empty critique notes, `body_unchanged` not true, empty hedge variables, hollow adversarial counterarguments, and score values outside 0 to 100.

#### Scenario: Refusal is rejected
- **WHEN** Anthropic returns `stop_reason = refusal`
- **THEN** the transport raises `LlmProviderError`

#### Scenario: Truncated output is rejected
- **WHEN** Anthropic returns `stop_reason = max_tokens`
- **THEN** the transport raises `LlmProviderError`

#### Scenario: Malformed role output is rejected
- **WHEN** a role output misses required fields or violates provider floors
- **THEN** the provider raises `LlmProviderError`

#### Scenario: Free generation does not invent missing investment fields
- **WHEN** free generation omits `direction`, `confidence`, or `verification_window`
- **THEN** the provider raises `LlmProviderError` and analysis stores no thesis

#### Scenario: Empty thesis provenance is preserved
- **WHEN** free generation returns `source_signal_ids = []`
- **THEN** analysis preserves the empty array so thesis validation can apply `no_source` uncertainty handling

### Requirement: Role Prompts And Thinking Policy

The provider MUST use role-specific system prompts and user prompts. Free generation, adversarial falsification, and target proposal MUST request adaptive thinking. Completeness critique MUST not request thinking. Reviewer prompts MUST use a hostile skeptic persona and must not produce `review_session`. Target proposal prompts MUST define `logic_score.score` as a 0-100 integer scale, include score anchors, and explicitly forbid 1-10 scoring. All role prompts MUST instruct the model to write human-readable prose, descriptions, rationales, notes, counterarguments, hedge variables, catalysts, and exit triggers in Simplified Chinese. Prompts MUST also instruct the model to keep existing enum field values as exact English tokens and never translate `direction`, `confidence`, or `buy_point.status`.

#### Scenario: Thinking policy is role-specific
- **WHEN** each role is invoked through injected transport
- **THEN** free generation, adversarial falsification, and target proposal pass adaptive thinking, while completeness critique passes no thinking

#### Scenario: Reviewer identity cannot be forged by model output
- **WHEN** adversarial falsification is returned
- **THEN** review session metadata is still created by orchestration, not by Claude

#### Scenario: Target score scale is explicit
- **WHEN** the target proposal role is invoked
- **THEN** the prompt instructs the model to emit `logic_score.score` as a 0-100 integer and not as a 1-10 score

#### Scenario: Human-readable output language is Chinese
- **WHEN** reasoner or target proposal prompts are built
- **THEN** system and user prompts instruct the model to write human-readable prose fields in Simplified Chinese

#### Scenario: Enum tokens remain English
- **WHEN** reasoner or target proposal prompts are built
- **THEN** system and user prompts instruct the model to keep `direction`, `confidence`, and `buy_point.status` values as exact English enum tokens

### Requirement: Usage And Secret Safety

Each LLM call MUST record usage metadata containing model, role, stop reason, input tokens, output tokens, and latency. Usage records MUST NOT include API keys or secrets.

#### Scenario: Usage record excludes secrets
- **WHEN** a provider call completes
- **THEN** usage metadata contains operational fields and no `ANTHROPIC_API_KEY` value

### Requirement: Offline Tests And Optional Live Smoke

Default tests MUST run offline with stub transports or fake Anthropic clients. A live smoke test MAY exist, but it MUST be skipped unless both `ANTHROPIC_API_KEY` and `RUN_LIVE_LLM` are set.

#### Scenario: Default tests do not touch network
- **WHEN** the test suite runs without live environment variables
- **THEN** no real Anthropic client or network call is required

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

