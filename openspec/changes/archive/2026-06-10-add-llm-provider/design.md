## Context

The pipeline is runnable end to end, but analysis and target generation still use stubs. Two production boundaries already exist: `analysis_orchestration.LlmReasoner` and `target_generation.LlmTargetProposer`. This change connects those boundaries to Claude through a narrow transport seam while preserving existing contracts and stores as the only persistence gates.

The governing risk is that `validate_thesis` and `validate_target` validate shape and confirmed-state gates, but they do not prove that model-produced `source_signal_ids` came from the provided context or that proposed `symbol` values are real. The provider layer must therefore reject provenance and symbol hallucinations before any orchestration layer can persist records.

## Goals / Non-Goals

**Goals:**
- Add `llm_provider.transport.Completion`, `AnthropicCompletion`, and `LlmProviderError`.
- Use Anthropic structured outputs through `client.messages.create(..., output_config={"format": {"type": "json_schema", "schema": ...}})`.
- Keep the Anthropic client lazy so imports and construction do not require keys or network.
- Replace the `NotImplementedError` bodies in `LlmReasoner` and `LlmTargetProposer` with provider-backed implementations.
- Hand-write output schemas that are strict role-output subsets, separate from `news_contracts` schemas.
- Enforce provenance, symbol universe, non-empty floors, score range, stop reasons, text-block presence, and JSON parsing failures as `LlmProviderError`.
- Keep all tests offline by injecting fake transports or fake Anthropic clients.

**Non-Goals:**
- No streaming.
- No prompt caching, batching, retry tuning, or custom timeout policy.
- No Pydantic parse API or strict tool-use mode.
- No real multi-provider independence.
- No changes to `pipeline_orchestration`, `news_contracts`, stores, or existing stubs.

## Decisions

**D1 Transport is the only SDK/network layer.** `Completion.__call__(*, system, user, schema, max_tokens, thinking)` returns parsed JSON data and records usage metadata. `AnthropicCompletion` is the only class that imports/constructs `anthropic.Anthropic`, and it does so lazily at first real call.

**D2 Structured output uses JSON schema output_config.** The provider passes `output_config={"format": {"type": "json_schema", "schema": schema}}` to `messages.create`, then reads the first text content block and parses it with `json.loads`. `stop_reason` values `refusal` and `max_tokens`, missing text, invalid JSON, and SDK errors all become `LlmProviderError`.

**D3 Output schemas are role fragments.** Schemas for free generation, completeness critique, adversarial falsification, and target candidates are handwritten. They contain only fields each role may author; orchestration still creates `track_record`, `review_session`, `status`, `state`, `priced_in`, and thesis links where appropriate. Every object declares all properties as required; optional semantics use nullable required fields.

**D4 Provider validation rejects hallucination.** `_enforce_provenance` checks every model-produced `source_signal_ids` array against provided signal ids. Empty thesis-level `source_signal_ids` are preserved so `thesis-contract` can apply `no_source` uncertainty instead of receiving fabricated provenance. Target generation is fail-closed: `LlmTargetProposer` requires an explicit `symbol_universe`, and candidate symbols outside it are rejected before storage. Neither check can be delegated to contract validation.

**D4a Required investment fields are not defaulted.** Free generation must provide valid `direction`, `confidence`, `falsifiable_expectation`, and `verification_window`. The analysis layer no longer invents neutral direction, medium confidence, or default windows for LLM provider output.

**D5 Author/reviewer independence is structural.** `LlmReasoner` instances carry different `ReasonerIdentity`, persona, and system prompts. The reviewer prompt is adversarial and is not allowed to stamp `review_session`; existing orchestration creates review metadata.

**D6 Usage is recorded without secrets.** Each provider call records model, role, stop reason, token counts, and latency. API keys are read from `ANTHROPIC_API_KEY` only by the SDK client and are never logged.

## Risks / Trade-offs

- Anthropic output schema support may strip unsupported JSON Schema constraints. -> Keep schemas simple and enforce floors/ranges in provider code.
- Same underlying model is not true statistical independence. -> State the limitation and keep true multi-provider review for a later change.
- Prompt compliance is not enough for provenance. -> Use prompt instructions plus post-parse subset checks.
- Live tests can be flaky or costly. -> Keep live smoke env-gated and assert only invariants.
- The project had no dependency file. -> Add a minimal `requirements.txt` with `anthropic`.

## Migration Plan

1. Add `llm-provider` delta spec and tasks.
2. Add `llm_provider` package with transport, schemas, prompt rendering, validation helpers, and usage records.
3. Wire `LlmReasoner` and `LlmTargetProposer` to the provider package while preserving existing stubs.
4. Add offline tests for transport parsing/errors, prompt/schema paths, provenance/symbol/range rejection, drift guards, key laziness, and env-gated live smoke.
5. Run `python3 -m pytest -q` and `openspec validate add-llm-provider --strict`.

## Open Questions

- Exact production prompt tuning after first real runs is deferred.
- Strict tool-use fallback is deferred and documented as an alternative, not implemented here.
