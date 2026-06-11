## Why

`scripts/run_live.py --pipeline` currently creates a temporary SQLite database and discards it after each run. That prevents theses, targets, track records, source cursors, and dedup history from accumulating across runs, which blocks the feedback loop from having durable data.

`ContractStore` already supports persistent reuse through idempotent table creation, source cursors, and persisted signal dedup. This change adds operation-layer entry points for a persistent store path and a read-only store summary.

## What Changes

- Add `scripts/run_live.py --pipeline --store PATH` to use a persistent `ContractStore(PATH)`.
- Keep existing tempfile behavior when `--store` is omitted.
- Create the parent directory for `--store` when missing.
- Print per-run `new_signal_count` and cumulative thesis/target counts.
- Add `scripts/run_live.py --show-store PATH` to print accumulated theses and targets without running providers.
- Add offline tests proving repeated runs against the same store are idempotent, distinct new signals accumulate, near-duplicates are rejected across runs, track records persist, and show-store prints expected fields.

## Capabilities

### New Capabilities

- `persistent-store`: operation-layer persistent SQLite store entry point and store summary display.

### Modified Capabilities

- `pipeline-orchestration`: live pipeline harness can use a persistent `ContractStore` path while the core pipeline remains composition-only.

## Impact

- Affected implementation:
  - `scripts/run_live.py`
  - tests
  - OpenSpec artifacts under `openspec/changes/add-persistent-store/`
- Explicitly not affected:
  - `news_contracts/storage.py`
  - `news_contracts` dedup/validation
  - `pipeline_orchestration`
  - `analysis_orchestration`
  - `llm_provider`
  - `target_generation`
  - `market_data`
  - `signal_clustering`
