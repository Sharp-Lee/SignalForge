## Why

Live multi-thesis pipeline runs exposed a reliability bug: target generation trusted model-authored candidate ids such as `candidate-1`, so repeated ids across theses triggered `UNIQUE constraint failed: targets.id` and dropped all targets for that thesis.

Target ids are system identity, not model output. A target represents a specific `symbol` under a specific thesis, so its stable id must be derived from `symbol|thesis_id`.

## What Changes

- Ignore `candidate["id"]` when assembling targets.
- Always derive target ids from `symbol` and `thesis["id"]`.
- Deduplicate repeated candidate symbols within a single thesis before target assembly and record a `rejected_reason`.
- Keep cross-thesis duplicate symbols legal because each thesis produces a different derived target id.
- Do not add broad `store.add_target()` exception handling; contract/storage errors must still surface.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `target-generation`: target assembly identity and duplicate-symbol handling.

## Impact

- Affected implementation:
  - `target_generation/core.py`
  - `tests/test_target_generation.py`
  - OpenSpec delta under `openspec/changes/fix-target-id-collision/`
- Explicitly not affected:
  - `llm_provider/`
  - `analysis_orchestration/`
  - `news_contracts/`
  - `market_data/`
  - dedup and signal clustering
  - transport/provider code
