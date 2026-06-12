# source-ingestion Specification

## Purpose
TBD - created by archiving change add-source-ingestion. Update Purpose after archive.
## Requirements
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

### Requirement: Injectable Real Fetcher Transports

Real fetchers MUST isolate bottom-level I/O behind injectable transports. RSS/Atom fetchers MUST use an injectable HTTP GET transport. last30days fetchers MUST use an injectable subprocess transport. Tests MUST run offline and MUST NOT perform real network calls or spawn a real last30days subprocess.

#### Scenario: RSS fetcher uses injected HTTP transport
- **WHEN** an RSS fetcher is constructed with a stub HTTP transport
- **THEN** it retrieves feed bytes from that transport and does not perform any direct network I/O

#### Scenario: last30days fetcher uses injected subprocess transport
- **WHEN** a last30days fetcher is constructed with a stub subprocess transport
- **THEN** it retrieves agent output from that transport and does not spawn a real subprocess

### Requirement: Cursor-driven Incremental Fetch

RSS/Atom real fetchers MUST use the supplied cursor as a published-time high-water mark and return only entries whose parsed `published_at` is newer than the cursor. RSS/Atom cursor filtering MUST be order-independent because real feeds commonly return newest entries first. Downstream dedup MUST remain as a safety net, not the primary RSS incremental mechanism.

last30days real fetchers MUST NOT invent unsupported cursor flags. last30days is a topic query tool rather than a pollable feed; it MUST accept configured topic(s), invoke the real CLI shape with the topic as a positional argument and `--emit=json`, and rely on downstream dedup for repeated per-topic research. The adapter MUST parse the real JSON report shape by extracting signal candidates from `items_by_source`; markdown report output MUST NOT be treated as a valid signal list.

#### Scenario: RSS second fetch skips already-seen entries
- **WHEN** an RSS fetcher receives a cursor from a previous run
- **THEN** it returns only feed entries whose parsed published time is newer than that cursor

#### Scenario: RSS newest-first feed keeps new entries
- **WHEN** a newest-first RSS feed contains one entry newer than the cursor and older entries after it
- **THEN** the fetcher returns the newer entry and does not drop it because of feed order

#### Scenario: last30days command uses real topic query shape
- **WHEN** a last30days fetcher is configured with a topic
- **THEN** the injected subprocess transport receives `python3 <script> <topic> --agent --emit=json` without any unsupported cursor flag

#### Scenario: last30days JSON report is normalized into attention signals
- **WHEN** last30days returns its real `--emit=json` report shape
- **THEN** the adapter extracts source items from `items_by_source` into `last30days_attention` signals that still pass `signal-contract`

### Requirement: Fetch And Normalize Failure Isolation

The runner MUST catch fetch-level failures from an adapter source, record them as source errors, skip cursor update for that failed source, and continue processing remaining sources. Fetch-level failure MUST NOT bypass the contracted write path or abort the entire ingestion run.

The runner MUST also catch normalize-level failures per raw item, record them as source rejections/errors, and continue processing remaining raw items and remaining sources. Normalize-level failure MUST NOT abort the entire ingestion run.

#### Scenario: Single source fetch failure is recorded
- **WHEN** one adapter raises during fetch
- **THEN** the runner records a source error for that adapter and continues

#### Scenario: Other sources continue after fetch failure
- **WHEN** one adapter fails during fetch and another adapter succeeds
- **THEN** the successful adapter still writes valid signals through `ContractStore.add_signal()`

#### Scenario: Failed source cursor is not advanced
- **WHEN** a source fails during fetch
- **THEN** the system does not update that source cursor

#### Scenario: Single raw item normalize failure is recorded
- **WHEN** an adapter raises while normalizing one raw item
- **THEN** the runner records a rejection and source error for that adapter

#### Scenario: Other sources continue after normalize failure
- **WHEN** one adapter fails during normalize and another adapter succeeds
- **THEN** the successful adapter still writes valid signals through `ContractStore.add_signal()`

### Requirement: Browser User Agent For RSS HTTP Fetch
The default RSS/Atom HTTP fetcher SHALL send a browser-like User-Agent when performing real HTTP requests. Injected HTTP transports used by tests MUST remain supported and MUST NOT perform real network I/O.

#### Scenario: Default RSS fetch uses browser headers
- **WHEN** the default RSS HTTP transport performs a real request
- **THEN** it includes a browser-like `User-Agent` header

#### Scenario: Injected transport remains isolated
- **WHEN** an RSS fetcher is constructed with an injected HTTP transport
- **THEN** the fetcher uses the injected transport and does not perform default HTTP request construction

