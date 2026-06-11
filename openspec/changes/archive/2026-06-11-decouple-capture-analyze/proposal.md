## Why

Daily RSS-only operation can produce far more accepted signals than the LLM path should process in one run. The current pipeline couples "newly captured in this run" to "immediately analyze all resulting clusters", so high-volume capture risks long runs, timeouts, noisy reports, and lost analysis opportunities after interruptions.

## What Changes

- Split live operation into a capture path and an analyze path:
  - capture: fetch configured sources and persist accepted signals only;
  - analyze: read pending accepted signals from the store, cluster them, select a small top-K set, run existing analysis/target generation, and leave the rest pending.
- Add a minimal pending/analyzed marker so accepted signals survive process crashes and can be analyzed in later runs.
- Add a configurable RSS source set with a small verified English global-tech/semiconductor feed list.
- Schedule capture frequently and analysis daily, keeping LLM work bounded.

## Capabilities

### New Capabilities
- `capture-analyze-flow`: Separates source capture from pending-signal analysis with a simple analysis marker and top-K budget.
- `source-feed-set`: Defines configurable RSS source lists and source verification expectations.

### Modified Capabilities
- `pipeline-orchestration`: Change the live path from before/after new-signal diff analysis to pending-signal analysis.
- `scheduled-run`: Split launchd scheduling into frequent capture and daily analysis.

## Impact

- Affected code areas after approval: `pipeline_orchestration/`, `source_ingestion/` configuration/adapter wiring, `scripts/`, `launchd/`, tests, and OpenSpec specs/tasks.
- Existing `analysis_orchestration.analyze()`, `target_generation.propose_targets()`, `llm_provider`, `news_contracts` contract schemas, dedup, and `signal_clustering` core logic stay unchanged.
- No new LLM provider behavior and no semantic/embedding ranking in this MVP.
