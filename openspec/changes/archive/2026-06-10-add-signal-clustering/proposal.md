## Why

The current pipeline turns every newly persisted signal from a run into one analysis group. After near-duplicate dedup was fixed, real RSS runs now preserve multiple distinct signals, but the pipeline still forces unrelated items into a single thesis. The ServeTheHome run demonstrated this failure mode: NAS, anniversary, NXP, Gigabyte cluster, RTX Spark mini-PC, and Microsoft Surface RTX Spark signals were merged into one over-broad thesis.

This change adds a deterministic signal clustering step before analysis so each coherent cluster produces its own thesis while isolated signals remain valid one-signal clusters.

## What Changes

- Add a `signal_clustering` module with an injectable clustering interface.
- Add a default deterministic, offline clusterer based on language-aware salient entity / term overlap with batch-local document-frequency filtering.
- Change `pipeline_orchestration.run_pipeline()` from "all new signals -> one group" to "new signals -> clusters -> one analysis per cluster".
- Keep per-unit failure isolation: analysis failure in one cluster MUST be recorded and MUST NOT prevent other clusters from producing theses or targets.
- Update `scripts/run_live.py --pipeline` printing if needed so multiple theses and their target results are visible.
- Add offline tests for English related/unrelated clustering, Chinese related/unrelated clustering, singleton clusters, and multi-cluster pipeline output.

## Capabilities

### New Capabilities

- `signal-clustering`: deterministic grouping of newly persisted signals into coherent analysis clusters before thesis generation.

### Modified Capabilities

- `pipeline-orchestration`: replace trivial single-group signal selection with injected signal clustering and per-cluster analysis/target generation.

## Impact

- Affected implementation:
  - `pipeline_orchestration/core.py`
  - new `signal_clustering/` module
  - `tests/`
  - `scripts/run_live.py` for multi-thesis display only if current output is too narrow
- Explicitly not affected:
  - `analysis_orchestration.analyze()` internals
  - `target_generation` core logic
  - `llm_provider/`
  - `news_contracts/` contracts, schemas, and dedup
  - embedding or LLM-based clustering
- The change is not archived until reviewer approval, tests, OpenSpec strict validation, and live pipeline verification complete.
