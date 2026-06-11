## MODIFIED Requirements

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
