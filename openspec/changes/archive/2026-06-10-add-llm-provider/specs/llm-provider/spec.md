## ADDED Requirements

### Requirement: Injectable Claude Transport

The LLM provider MUST isolate SDK and network access behind an injectable `Completion` transport. The default Anthropic transport MUST lazily construct its client only at first real call, read the API key from `ANTHROPIC_API_KEY`, use model `claude-opus-4-8`, and call `messages.create` with JSON-schema structured output through `output_config.format`.

#### Scenario: Lazy client construction
- **WHEN** `LlmReasoner`, `LlmTargetProposer`, or `AnthropicCompletion` is imported or constructed without an API key
- **THEN** no Anthropic client is created and no network call is attempted

#### Scenario: Structured output request
- **WHEN** a real Claude completion is invoked
- **THEN** the transport sends `system`, `user`, a generated JSON schema, `max_tokens`, and the role's thinking setting to `messages.create`

### Requirement: Role Fragment Schemas

The provider MUST use handwritten output schemas that are strict role-fragment subsets of the canonical contracts. The model MUST NOT author orchestration-owned fields such as `track_record`, `review_session`, `status`, target `state`, `priced_in`, or linked `thesis_ids`.

Every object in generated schemas MUST set `additionalProperties: false` and MUST list every declared property in `required`. Fields that are truly optional MUST be represented as nullable required fields rather than omitted optional properties.

#### Scenario: Free generation returns thesis fragment
- **WHEN** `LlmReasoner.reason("free_generation", context)` is called
- **THEN** it returns only free-generation fields consumed by analysis orchestration

#### Scenario: Target proposer returns candidate fragment
- **WHEN** `LlmTargetProposer.propose(thesis)` is called
- **THEN** it returns candidate fragments without target `state`, `priced_in`, or `thesis_ids`

#### Scenario: Schema drift guard passes
- **WHEN** generated role schemas are compared to canonical contract schema fields
- **THEN** every emitted field is either allowed by the relevant contract or explicitly orchestration-local

#### Scenario: Generated schemas are all-required
- **WHEN** generated schemas are inspected before a live Claude call
- **THEN** every object has `required` equal to its declared `properties`

### Requirement: Provenance And Symbol Enforcement

The provider MUST reject hallucinated provenance and invalid symbols. Every model-produced `source_signal_ids` array MUST be a subset of the provided signal ids. `LlmTargetProposer` MUST fail closed unless an explicit `symbol_universe` is provided; every proposed target symbol MUST be in that universe.

#### Scenario: Hallucinated signal id is rejected
- **WHEN** Claude returns a `source_signal_ids` value not present in `PROVIDED_SIGNAL_IDS`
- **THEN** the provider raises `LlmProviderError` and returns no partial role output

#### Scenario: Out-of-universe symbol is rejected
- **WHEN** a target candidate symbol is outside the configured symbol universe
- **THEN** the provider raises `LlmProviderError` and returns no candidates

#### Scenario: Missing symbol universe is rejected before target generation
- **WHEN** `LlmTargetProposer.propose()` is called without a `symbol_universe`
- **THEN** the provider raises `LlmProviderError` before calling transport or storing targets

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

The provider MUST use role-specific system prompts and user prompts. Free generation, adversarial falsification, and target proposal MUST request adaptive thinking. Completeness critique MUST not request thinking. Reviewer prompts MUST use a hostile skeptic persona and must not produce `review_session`.

#### Scenario: Thinking policy is role-specific
- **WHEN** each role is invoked through injected transport
- **THEN** free generation, adversarial falsification, and target proposal pass adaptive thinking, while completeness critique passes no thinking

#### Scenario: Reviewer identity cannot be forged by model output
- **WHEN** adversarial falsification is returned
- **THEN** review session metadata is still created by orchestration, not by Claude

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
