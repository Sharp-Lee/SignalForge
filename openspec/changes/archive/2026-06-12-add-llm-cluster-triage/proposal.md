## Why

After broadening RSS capture to the full AI ecosystem, pending clusters can grow into the hundreds. Keyword top-K is a useful deterministic fallback, but it cannot reliably distinguish genuinely tradeable AI ecosystem signals from generic commentary, vendor marketing, or broad technology noise.

This change adds a small LLM triage step before analysis so the system spends expensive ③/④ reasoning on the clusters most likely to matter for a personal A-share alpha research workflow.

## What Changes

- Add an LLM-backed cluster triage selector for `analyze_pending()`.
- Keep the existing keyword `_select_top_clusters()` path as a mandatory fallback when triage fails, returns invalid output, or returns no selections.
- Limit triage candidates by freshness when pending clusters exceed a fixed upper bound, so the triage prompt stays bounded without reintroducing keyword pre-filtering.
- Add a triage prompt, JSON schema, and enforce function that fails closed when the model invents cluster ids.
- Persist or carry selected-cluster reasons so downstream output can explain why each cluster was chosen.
- Keep analysis, target generation, contracts, digest rendering, market data, clustering, and dedup internals unchanged.

## Capabilities

### New Capabilities

### Modified Capabilities
- `capture-analyze-flow`: Replace direct keyword top-K selection with optional LLM triage selection plus keyword fallback.
- `llm-provider`: Add a bounded triage role/schema/enforcement path for cluster selection.

## Impact

- Affected code after approval:
  - `pipeline_orchestration/core.py`
  - `llm_provider/prompts.py`
  - `llm_provider/schemas.py`
  - `llm_provider/validation.py`
  - tests for triage success/fallback/enforcement/freshness cap
- No changes to:
  - `analysis_orchestration.analyze()`
  - `target_generation.propose_targets()`
  - contract schemas
  - digest generation
  - market data
  - RSS capture
