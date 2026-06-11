## ADDED Requirements

### Requirement: OpenAI-Compatible Completion Transport

The system MUST provide `OpenAICompatibleCompletion` implementing the existing `Completion` protocol. It MUST accept `model`, `base_url`, `api_key_env`, `json_mode`, and optional `client` constructor parameters. It MUST read the API key from the environment variable named by `api_key_env`, not from a raw key value.

#### Scenario: Lazy OpenAI-compatible client
- **WHEN** an `OpenAICompatibleCompletion` is constructed without an API key
- **THEN** no SDK client is created until the first call

#### Scenario: OpenAI-compatible response parses as object
- **WHEN** a compatible response returns JSON object text in `choices[0].message.content`
- **THEN** the transport returns the parsed dictionary

### Requirement: JSON Response Modes

`OpenAICompatibleCompletion` MUST support `json_mode="schema"` and `json_mode="object"`. Schema mode MUST send OpenAI-compatible `response_format.type = json_schema` with strict schema. Object mode MUST send `response_format.type = json_object` and append the schema to the user prompt.

#### Scenario: Schema mode sends response schema
- **WHEN** `json_mode` is `schema`
- **THEN** the SDK request includes `response_format` with `json_schema.name`, `json_schema.schema`, and `json_schema.strict = true`

#### Scenario: Object mode appends schema to prompt
- **WHEN** `json_mode` is `object`
- **THEN** the SDK request uses `json_object` and the user prompt contains the serialized schema

### Requirement: OpenAI-Compatible Error Discipline

The transport MUST raise `LlmProviderError` for finish reasons `length` and `content_filter`, invalid JSON, non-object JSON, missing choices/content, or SDK call failures. It MUST NOT return partial defaults.

#### Scenario: Length finish is rejected
- **WHEN** the response finish reason is `length`
- **THEN** the transport raises `LlmProviderError`

#### Scenario: Content filter finish is rejected
- **WHEN** the response finish reason is `content_filter`
- **THEN** the transport raises `LlmProviderError`

#### Scenario: Non-object JSON is rejected
- **WHEN** the response content parses to an array or scalar
- **THEN** the transport raises `LlmProviderError`

### Requirement: Anthropic Base URL Remains Optional

`AnthropicCompletion` MUST accept an optional `base_url` constructor parameter and pass it to `anthropic.Anthropic`. When `base_url` is `None`, existing default SDK behavior MUST remain unchanged.

#### Scenario: Anthropic base URL passed through
- **WHEN** `AnthropicCompletion(base_url=...)` first creates its client
- **THEN** the Anthropic SDK receives that `base_url`

### Requirement: Existing Provider Consumers Remain Stable

The change MUST NOT alter the `Completion` protocol signature, prompts, schemas, enforcement helpers, `LlmReasoner`, or `LlmTargetProposer`.

#### Scenario: Existing stub round trip still works
- **WHEN** existing stub transports are used through `analyze()` or `propose_targets()`
- **THEN** the provider protocol remains compatible and existing validations still pass
