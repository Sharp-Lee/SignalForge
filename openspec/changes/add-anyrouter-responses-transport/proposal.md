## Why

AnyRouter's documented Codex integration uses OpenAI's Responses API (`wire_api = "responses"`), while the current project transports only cover Anthropic Messages and OpenAI-compatible Chat Completions. We need a Responses API transport so AnyRouter can be tested through the existing `Completion` seam.

## What Changes

- Add `ResponsesAPICompletion` implementing the existing `Completion` protocol.
- Support `json_mode="schema"` via Responses API `text.format` JSON schema.
- Support `json_mode="object"` by appending the schema to the prompt and requesting JSON object output.
- Keep SDK/client construction lazy and read the token from a named environment variable.
- Parse Responses API output into a dictionary and raise `LlmProviderError` on incomplete/failed/non-JSON/non-object output.
- Export the new transport.
- Update `scripts/run_live.py` so relay can use `RELAY_FORMAT=responses`.

## Capabilities

### New Capabilities

- `responses-provider`: Responses API transport support for AnyRouter/Codex-style endpoints.

### Modified Capabilities

（无。Existing Anthropic, OpenAI-compatible Chat Completions, prompts, schemas, and enforcement helpers remain unchanged.）

## Impact

- Affected code:
  - `llm_provider/transport.py`
  - `llm_provider/__init__.py`
  - `scripts/run_live.py`
  - `tests/test_llm_provider.py`
- Existing `Completion` consumers keep the same interface.
