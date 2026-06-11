## ADDED Requirements

### Requirement: Adapter Protocol

The system MUST define a source Adapter protocol that separates raw retrieval from contract normalization. Each Adapter MUST expose a stable `source_id`, `fetch(cursor)` that returns raw source items and a next cursor, and `normalize(raw_item)` that returns zero or more `signal-contract` records. Network I/O MUST be injectable so adapters can be tested with offline fixtures.

#### Scenario: Adapter normalizes fixture without network
- **WHEN** an Adapter is constructed with a fixture fetcher and run with a cursor
- **THEN** it fetches raw fixture items and normalizes them into signal-contract records without making a network call

#### Scenario: Invalid raw item can normalize to no signal
- **WHEN** a raw source item lacks enough data to satisfy signal-contract
- **THEN** the Adapter may return no normalized signal for that raw item rather than writing invalid data

### Requirement: Contracted Write Path

Every normalized signal MUST be written through `ContractStore.add_signal()`. The ingestion layer MUST NOT perform its own persistence bypass, schema validation, or deduplication logic. Rejected signals MUST be reported in the run result without stopping the entire source run.

#### Scenario: Valid normalized signal is persisted through store
- **WHEN** a source run produces a valid normalized signal
- **THEN** the runner writes it through `ContractStore.add_signal()` and the signal appears in the `signals` table

#### Scenario: Duplicate normalized signal is reported and skipped
- **WHEN** a repeated source run produces a near-duplicate or already-written signal
- **THEN** the runner reports the rejection and does not create a duplicate signal row

### Requirement: Incremental Cursor Idempotency

The system MUST reuse `source_cursors` to persist one opaque cursor per source. Re-running a source with the same already-processed data MUST be idempotent and MUST NOT duplicate accepted signals. Cursor updates MUST be source-scoped.

#### Scenario: Source cursor is saved after run
- **WHEN** a source run completes with a next cursor
- **THEN** the system saves that cursor under the adapter source id in `source_cursors`

#### Scenario: Re-running source is idempotent
- **WHEN** the same source run is executed twice with the same fixture data
- **THEN** the second run does not add duplicate signal rows

### Requirement: Reference Global Adapters

The system MUST provide small reference Adapters for RSS/Atom-shaped data, GDELT-shaped fixture data, and existing last30days agent output. These adapters MUST produce signal-contract records with the correct `signal_origin` and source provenance.

#### Scenario: RSS item becomes news signal
- **WHEN** an RSS or Atom fixture item has title, link, timestamp, and body
- **THEN** the RSS Adapter normalizes it to `signal_origin = news`

#### Scenario: GDELT item becomes news signal
- **WHEN** a GDELT-shaped fixture item has url, title, timestamp, and summary
- **THEN** the GDELT Adapter normalizes it to `signal_origin = news`

#### Scenario: last30days output uses attention origin
- **WHEN** last30days agent output is run through the unified Adapter
- **THEN** it normalizes to `signal_origin = last30days_attention`

### Requirement: Reverse Intake Skeleton

The system MUST provide a reverse-intake Adapter skeleton for injected market move records. It MUST normalize a market move and its backtraced news into a `signal_origin = market_move` signal with `trigger_reason`. The normalized signal MUST pass existing signal-contract event hard gate before persistence.

#### Scenario: Market move fixture becomes market_move signal
- **WHEN** a market move fixture includes backtraced news provenance and a hard-gate trigger reason
- **THEN** the reverse-intake Adapter normalizes it to a valid `market_move` signal

#### Scenario: Weak market move is rejected by contract store
- **WHEN** a market move fixture lacks any hard-gate trigger reason
- **THEN** the runner reports rejection and does not persist it

### Requirement: Thin One-shot Runner

The system MUST provide a thin runner that can execute one or more adapters once. The runner MUST return per-source accepted and rejected counts, and MUST NOT implement daily/event/weekly scheduling strategy.

#### Scenario: Runner executes selected source once
- **WHEN** the caller passes one Adapter to the runner
- **THEN** the runner fetches, normalizes, writes through the store, updates the source cursor, and returns counts for that source

#### Scenario: Runner does not schedule by cadence
- **WHEN** the runner completes a source run
- **THEN** it does not decide daily, event, or weekly cadence and leaves scheduling to future orchestration
