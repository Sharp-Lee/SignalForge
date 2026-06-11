## Context

`LlmReasoner` and `LlmTargetProposer` depend only on the `Completion` protocol. `AnthropicCompletion` currently implements that protocol and is the only real transport. This change adds an OpenAI-compatible implementation as a pure transport-layer increment.

## Goals / Non-Goals

**Goals:**
- Add `OpenAICompatibleCompletion` implementing the existing `Completion` protocol.
- Support schema mode and JSON object mode.
- Keep OpenAI SDK client creation lazy.
- Map OpenAI-compatible response content and usage into existing `LlmProviderError` and `UsageRecord` behavior.
- Add optional Anthropic `base_url` support.

**Non-Goals:**
- No changes to prompts, schemas, enforcement helpers, reasoner/proposer classes, or pipeline orchestration.
- No provider routing policy.
- No retries, streaming, batching, or cache behavior.

## Decisions

**D1 Completion protocol stays unchanged.** `OpenAICompatibleCompletion.__call__` accepts `thinking` because the protocol requires it, but ignores it because OpenAI-compatible chat completions do not use Anthropic thinking.

**D2 Schema mode uses response_format json_schema.** `json_mode="schema"` sends `response_format={"type": "json_schema", "json_schema": {"name": schema title, "schema": schema, "strict": True}}`.

**D3 Object mode appends schema to the prompt.** `json_mode="object"` sends `response_format={"type": "json_object"}` and appends the schema JSON to the user prompt so providers without schema support can still receive the contract.

**D4 Response extraction is minimal and explicit.** The transport reads `response.choices[0].message.content`, parses JSON, and requires the result to be an object. `finish_reason` values `length` and `content_filter` are fatal.

**D5 Usage shape stays shared.** Usage maps `prompt_tokens` to `input_tokens` and `completion_tokens` to `output_tokens`, using the same `UsageRecord` dataclass as Anthropic.

## Risks / Trade-offs

- OpenAI-compatible providers vary in schema support. -> Provide both schema and object modes.
- Some providers return malformed or non-object JSON. -> Raise `LlmProviderError` and return no partial defaults.
- Base URL misconfiguration can fail at runtime. -> Keep construction lazy and surface failures through provider errors.

## Migration Plan

1. Add OpenAI-compatible transport and export.
2. Add dependency declaration.
3. Extend offline fake-client tests.
4. Run full tests and OpenSpec strict validation.

## Open Questions

- Provider selection/routing policy remains a later change.
