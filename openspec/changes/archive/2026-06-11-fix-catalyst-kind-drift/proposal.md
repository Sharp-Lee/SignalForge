## Why

Live target generation exposed a bridge drift: the LLM proposal schema permits `kind: null` / `value: null` for catalyst metadata, while `target-contract` allows those fields to be omitted but rejects them when present as non-strings. Passing model `null` values through unchanged causes otherwise valid targets to be rejected and lost.

## What Changes

- Normalize candidate catalysts before target persistence by dropping optional keys whose value is `None`.
- Apply the same normalization to exit triggers defensively.
- Keep `description` and all non-null metadata unchanged.
- Do not change target contract schema, LLM proposal schema, target enforcement, or prompt behavior.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `target-generation`: target assembly must bridge nullable proposal metadata into contract-compliant optional fields.

## Impact

- Affected implementation:
  - `target_generation/core.py`
  - `tests/test_target_generation.py`
  - OpenSpec delta under `openspec/changes/fix-catalyst-kind-drift/`
- Explicitly not affected:
  - `news_contracts/` schemas or validators
  - `llm_provider/` schemas, prompts, or enforcement
  - `analysis_orchestration/`
  - dedup, signal clustering, and market data
