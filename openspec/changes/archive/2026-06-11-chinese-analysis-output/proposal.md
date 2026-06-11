## Why

Live analysis currently follows English RSS source language and produces English thesis and target prose. The daily digest is intended for Chinese-speaking family and friends, so human-readable analysis output must be Simplified Chinese while contract enum tokens remain machine-valid English.

## What Changes

- Add explicit Simplified Chinese prose instructions to all LLM role system prompts.
- Add the same language and enum-token guardrails to reasoner and target user prompts.
- Keep schema, transport, enforcement, analysis orchestration, target generation, and digest code unchanged.
- Verify with offline prompt tests and a live DeepSeek run that prose is Chinese and enum fields still pass validation.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `llm-provider`: Role prompts must request Simplified Chinese for human-readable prose fields while preserving English enum tokens.

## Impact

- Affected code: `llm_provider/prompts.py`.
- Affected tests: prompt text coverage under `tests/`.
- No dependency, data model, transport, schema, validation, or persistence changes.
