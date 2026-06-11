## ADDED Requirements

### Requirement: Responses API Completion Transport

The system MUST provide `ResponsesAPICompletion` implementing the existing `Completion` protocol for OpenAI Responses API compatible endpoints. It MUST accept `model`, `base_url`, `api_key_env`, `json_mode`, and optional `client` constructor parameters.

#### Scenario: Lazy Responses client
- **WHEN** a `ResponsesAPICompletion` is constructed
- **THEN** no SDK client is created until the first completion call

#### Scenario: Responses output parses as object
- **WHEN** a Responses API response returns JSON object text
- **THEN** the transport returns the parsed dictionary

### Requirement: Responses JSON Modes

The transport MUST support `json_mode="schema"` using Responses API `text.format` JSON schema and `json_mode="object"` using JSON object mode with the schema appended to the prompt.

#### Scenario: Schema mode sends text format schema
- **WHEN** `json_mode` is `schema`
- **THEN** the SDK request includes `text.format.type = json_schema`, schema name, schema body, and strict true

#### Scenario: Object mode appends schema
- **WHEN** `json_mode` is `object`
- **THEN** the SDK request includes `text.format.type = json_object` and the user prompt contains the schema JSON

### Requirement: Responses Error Discipline

The transport MUST raise `LlmProviderError` for incomplete or failed responses, missing text output, invalid JSON, or non-object JSON. It MUST NOT return partial defaults.

#### Scenario: Incomplete response is rejected
- **WHEN** a Responses API response has status `incomplete`
- **THEN** the transport raises `LlmProviderError`

#### Scenario: Non-object JSON is rejected
- **WHEN** output parses to an array or scalar
- **THEN** the transport raises `LlmProviderError`

### Requirement: Live Harness Relay Support

`scripts/run_live.py` MUST support `RELAY_FORMAT=responses` and route relay calls through `ResponsesAPICompletion`.

#### Scenario: Relay responses format selects Responses transport
- **WHEN** `RELAY_FORMAT=responses`
- **THEN** the live harness constructs `ResponsesAPICompletion` with relay model, base URL, API key env, and JSON mode
