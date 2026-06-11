# persistent-store Specification

## Purpose
TBD - created by archiving change add-persistent-store. Update Purpose after archive.
## Requirements
### Requirement: Persistent Pipeline Store Path

The live run harness SHALL allow `--pipeline --store PATH` to run the pipeline against a persistent `ContractStore(PATH)`. It MUST create the parent directory when missing. When `--store` is omitted, the harness MUST keep using a temporary store. Operation-layer scheduled runners MAY call the harness with a stable persistent store path.

#### Scenario: Pipeline uses supplied store path
- **WHEN** `scripts/run_live.py --pipeline --store PATH` runs
- **THEN** the pipeline uses `ContractStore(PATH)` and durable rows remain after the process exits

#### Scenario: Pipeline without store remains temporary
- **WHEN** `scripts/run_live.py --pipeline` runs without `--store`
- **THEN** the harness uses a temporary database and does not require a persistent path

#### Scenario: Scheduled wrapper uses stable persistent store
- **WHEN** the scheduled wrapper invokes the live pipeline
- **THEN** it supplies a stable store path so source cursors, theses, targets, and track records accumulate across runs

### Requirement: Repeated Runs Are Incremental

The persistent pipeline store SHALL preserve source cursors, signals, theses, targets, and track records across runs. Re-running the same feed against the same store MUST NOT duplicate previously ingested signals or create duplicate theses/targets from those signals.

#### Scenario: Same feed second run has no new signals
- **WHEN** the same source feed is run twice against the same store without new items
- **THEN** the second run reports zero newly accepted signals and cumulative thesis/target counts do not increase

#### Scenario: New distinct signal accumulates
- **WHEN** a later run against the same store receives a distinct new signal
- **THEN** the store accumulates an additional thesis and associated track record

#### Scenario: Cross-run near duplicate is rejected
- **WHEN** a later run against the same store receives a near-duplicate of an existing signal
- **THEN** the signal is rejected by existing store dedup history and no new thesis is created

### Requirement: Show Store Summary

The live run harness SHALL provide `--show-store PATH` to print accumulated thesis and target summaries without running ingestion, LLM, target generation, market data, or other providers.

#### Scenario: Show store prints thesis and target rows
- **WHEN** `scripts/run_live.py --show-store PATH` is run for an existing store
- **THEN** it prints total thesis and target counts plus the required summary fields for each row

#### Scenario: Missing store path fails clearly
- **WHEN** `scripts/run_live.py --show-store PATH` points to a missing file
- **THEN** it exits with a clear message instead of creating or summarizing an unintended empty store

