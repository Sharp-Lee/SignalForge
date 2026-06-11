## Context

AnyRouter exposes a Codex configuration that uses `wire_api = "responses"` at `https://anyrouter.top/v1`. The existing `OpenAICompatibleCompletion` targets Chat Completions and is therefore the wrong transport for this endpoint. The new transport must implement the same `Completion` protocol so `LlmReasoner` and `LlmTargetProposer` can use it without changes.

## Goals / Non-Goals

**Goals:**
- Add a Responses API transport that returns parsed JSON dictionaries.
- Keep the client lazy and configurable through `base_url`, `model`, and `api_key_env`.
- Support schema and object JSON modes.
- Record usage in the existing `UsageRecord` shape.
- Add offline fake-client tests and wire `run_live.py` to `RELAY_FORMAT=responses`.

**Non-Goals:**
- No changes to prompts, schemas, enforcement helpers, reasoner/proposer classes, or store validation.
- No provider routing policy.
- No streaming, retries, batching, or caching.

## Decisions

**D1 Transport name is `ResponsesAPICompletion`.** This keeps it distinct from `OpenAICompatibleCompletion`, whose implementation is specifically Chat Completions.

**D2 Responses structured output uses `text.format`.** In schema mode the request sends `text={"format": {"type": "json_schema", "name": ..., "schema": ..., "strict": True}}`.

**D3 Object mode is the fallback.** In object mode the transport sends `text={"format": {"type": "json_object"}}` and appends the schema JSON to the user prompt.

**D4 Output extraction supports SDK convenience and object shape.** The transport first reads `response.output_text` when present, then falls back to traversing `response.output[*].content[*].text`.

**D5 Failure remains fail-closed.** Incomplete/failed responses, invalid JSON, non-object JSON, or missing output raise `LlmProviderError`.

## Risks / Trade-offs

- AnyRouter may not support `text.format` schema mode. -> Provide object mode fallback.
- Responses API object shapes can vary between SDK versions and relays. -> Support `output_text` and nested output/content text extraction.
- Thinking/reasoning support varies. -> The transport accepts `thinking` for protocol compatibility but does not pass it by default.

## Migration Plan

1. Add `ResponsesAPICompletion` and export it.
2. Add tests with fake Responses API client.
3. Update `run_live.py` to support `RELAY_FORMAT=responses`.
4. Run full tests and OpenSpec strict validation.

## Open Questions

- Whether AnyRouter supports schema mode or needs object mode will be determined by live smoke.
