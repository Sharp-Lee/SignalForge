## 1. LLM Provider Triage Role

- [x] 1.1 Add cluster triage prompt rendering with bounded candidate cluster input and Chinese reason instructions.
- [x] 1.2 Add strict `CLUSTER_TRIAGE_SCHEMA` with `selected[].cluster_id` and `selected[].reason`.
- [x] 1.3 Add `enforce_cluster_triage_output()` that rejects hallucinated cluster ids, malformed selected items, and empty reasons.
- [x] 1.4 Add a small `LlmClusterTriageSelector` wrapper that uses injected `Completion` transport and returns selected cluster ids with reasons.

## 2. Analyze Path Integration

- [x] 2.1 Extend `signal_analysis_state` idempotently with nullable `triage_reason`.
- [x] 2.2 Add freshness-bounded triage candidate selection with default `triage_candidate_limit = 200`.
- [x] 2.3 Integrate optional triage selector into `analyze_pending()` / `run_pipeline()`, with keyword top-K fallback on no selector, triage error, invalid output, or empty selection.
- [x] 2.4 Persist triage reasons for selected cluster signals without modifying thesis or target contract payloads.

## 3. Offline Tests

- [x] 3.1 Test triage prompt/schema/enforcement success and hallucinated id failure.
- [x] 3.2 Test triage success selects model-chosen clusters and persists `triage_reason`.
- [x] 3.3 Test triage error, invalid/unknown id, and empty selection fall back to keyword top-K.
- [x] 3.4 Test candidate overflow sends newest clusters by published time, not keyword score.

## 4. Verification

- [x] 4.1 Run `python -m pytest tests/ -q`.
- [x] 4.2 Run `openspec validate add-llm-cluster-triage --strict`.
- [x] 4.3 Run live `--analyze` evidence against a safe copy or live store and capture redacted stdout showing AI triage reasons, thesis generation, digest generation, and usage/cost.

## 5. Commit

- [x] 5.1 Scan staged changes for secrets.
- [x] 5.2 Commit and push main, including the previously pending OpenSpec archive moves.
