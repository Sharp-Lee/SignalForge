## Why

The current LLM provider layer only has an Anthropic transport. We need the same `Completion` protocol to support OpenAI-compatible APIs such as DeepSeek, relays, and OpenAI without changing reasoner/proposer code.

## What Changes

- Add `OpenAICompatibleCompletion` to `llm_provider/transport.py`.
- Support two JSON response modes:
  - `json_mode="schema"` uses OpenAI-compatible `response_format={"type":"json_schema", ...}`.
  - `json_mode="object"` uses `response_format={"type":"json_object"}` and appends the schema to the user prompt.
- Preserve the existing `Completion` protocol signature and ignore `thinking` for OpenAI-compatible calls.
- Add optional `base_url` support to `AnthropicCompletion` without changing existing default behavior.
- Record usage in the existing `UsageRecord` shape.
- Add `openai>=1.0.0` to dependencies.
- Extend provider tests with fake OpenAI-compatible clients, error branches, lazy-client checks, and JSON object mode prompt assertions.

## Capabilities

### New Capabilities

- `multi-provider`: OpenAI-compatible transport support for the existing LLM provider seam.

### Modified Capabilities

（无。Existing provider behavior remains compatible; this change adds a new transport implementation and an optional Anthropic base URL parameter.）

## Impact

- Affected code:
  - `llm_provider/transport.py`
  - `llm_provider/__init__.py`
  - `requirements.txt`
  - `tests/test_llm_provider.py`
- Existing `Completion` consumers keep the same interface.
- Existing Anthropic behavior is unchanged when `base_url` is not supplied.
