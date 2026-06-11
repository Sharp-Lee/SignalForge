## 1. Planning

- [x] 1.1 Validate `add-llm-provider` planning artifacts with OpenSpec strict mode
- [x] 1.2 Add Anthropic dependency declaration

## 2. Transport Layer

- [x] 2.1 Create `llm_provider` module structure
- [x] 2.2 Define `Completion` protocol, `AnthropicCompletion`, `LlmProviderError`, and usage records
- [x] 2.3 Implement lazy Anthropic client creation and JSON-schema `output_config` requests
- [x] 2.4 Convert API errors, refusal, max_tokens, missing text, and invalid JSON into `LlmProviderError`

## 3. Role Schemas And Prompts

- [x] 3.1 Implement handwritten schemas for free generation, completeness critique, adversarial review, and target candidates
- [x] 3.2 Implement role-specific system and user prompt rendering
- [x] 3.3 Apply role-specific thinking policy
- [x] 3.4 Add schema drift guard helpers

## 4. Provider Validation

- [x] 4.1 Enforce `source_signal_ids` subset checks for thesis, claims, and transmission steps
- [x] 4.2 Fail closed unless target symbol universe is explicitly configured
- [x] 4.3 Enforce non-empty notes, hedge variables, adversarial counterargument, and score range
- [x] 4.4 Reject hollow adversarial counterarguments

## 5. Boundary Integration

- [x] 5.1 Replace `LlmReasoner.reason()` NotImplementedError with provider-backed implementation
- [x] 5.2 Replace `LlmTargetProposer.propose()` NotImplementedError with provider-backed implementation
- [x] 5.3 Preserve existing stubs and orchestration signatures
- [x] 5.4 Keep provider output flowing through existing `analyze()` and `propose_targets()` paths

## 6. Tests And Verification

- [x] 6.1 Add offline stub transport tests for all roles and thinking policy
- [x] 6.2 Add AnthropicCompletion fake-client tests for parsing and error branches
- [x] 6.3 Add failure tests for provenance, missing required fields, empty source ids, symbol universe, malformed outputs, score range, empty notes, empty hedges, and hollow counterarguments
- [x] 6.4 Add dependency laziness and key-safety tests
- [x] 6.5 Add schema drift guard tests
- [x] 6.6 Add env-gated live smoke test skipped by default
- [x] 6.7 Run `python3 -m pytest -q`
- [x] 6.8 Run `openspec validate add-llm-provider --strict`
