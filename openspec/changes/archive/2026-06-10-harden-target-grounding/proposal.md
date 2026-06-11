## Why

The first live DeepSeek target-generation run exposed two grounding failures that offline stubs did not catch: target scores were emitted on a 1-10 scale while the system gates use 0-100, and candidate company names could be hallucinated even when symbols were in the allowed universe.

## What Changes

- Pin target `logic_score.score` semantics in target prompts to a 0-100 integer scale with explicit anchors and an explicit ban on 1-10 scoring.
- Change target symbol universe inputs from `set[str]` to authoritative `dict[str, str]` reference data mapping symbol to company name.
- Remove model-authored `name` from target proposal output schema.
- Stamp candidate `name` from the authoritative universe before target assembly so downstream target records still satisfy `target-contract`.
- Keep out-of-universe symbols fail-closed.
- Decide whether non-hallucination candidate malformations such as missing catalysts should keep rejecting the whole batch or become per-candidate rejection reasons.
- Update harness fixture and tests to use authoritative symbol-name mappings.
- Verify with a real DeepSeek `--targets` run, not only offline tests.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `llm-provider`: target proposal prompts, target proposal schema, and symbol/name enforcement are changing.
- `target-generation`: target generation consumes authoritative symbol-name mappings and persists only system-stamped target names.

## Impact

- Affected code:
  - `llm_provider/prompts.py`
  - `llm_provider/schemas.py`
  - `llm_provider/validation.py`
  - `target_generation/core.py`
  - `scripts/run_live.py`
  - `tests/`
- No transport changes.
- No analysis orchestration changes.
- No market-data changes; live harness price layer remains a stub.
- No archive as part of this change.
