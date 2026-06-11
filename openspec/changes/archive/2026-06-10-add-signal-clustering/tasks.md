## 1. Design Gate

- [x] 1.1 Confirm R1-fix: DF-adaptive language-aware salient-overlap evidence table and thresholds.

## 2. Signal Clustering Module

- [x] 2.1 Add `signal_clustering` package with `SignalCluster`, `SignalClusterer`, and default deterministic clusterer.
- [x] 2.2 Implement clustering-only normalization and CJK ratio routing.
- [x] 2.3 Implement batch-local DF filtering with `df_cutoff = ceil(batch_size * 0.5)` and no hand-maintained stopword table.
- [x] 2.4 Implement English salient-term extraction, Chinese significant-term extraction, pair thresholds, connected components, and singleton fallback.

## 3. Pipeline Integration

- [x] 3.1 Update `pipeline_orchestration.run_pipeline()` to accept an optional clusterer and analyze each cluster independently.
- [x] 3.2 Preserve per-cluster analysis failure isolation and per-thesis target-generation failure isolation.
- [x] 3.3 Keep all thesis/target persistence through existing layer functions and `ContractStore`.

## 4. Tests

- [x] 4.1 Add offline English fixtures proving related signals cluster and unrelated ServeTheHome signals stay separate.
- [x] 4.2 Add offline Chinese fixtures proving related signals cluster and unrelated Chinese signals stay separate.
- [x] 4.3 Add singleton and small-batch safe-degradation tests.
- [x] 4.4 Add pipeline tests proving multiple clusters produce multiple theses and one cluster failure does not block other clusters.

## 5. Live Harness

- [x] 5.1 Update `scripts/run_live.py --pipeline` only as needed to print multiple theses and target groups clearly.

## 6. Verification

- [x] 6.1 Run full `pytest tests/ -q`.
- [x] 6.2 Run `openspec validate add-signal-clustering --strict`.
- [x] 6.3 Run the ServeTheHome live pipeline gate and confirm multiple coherent theses with validated thesis outputs.
