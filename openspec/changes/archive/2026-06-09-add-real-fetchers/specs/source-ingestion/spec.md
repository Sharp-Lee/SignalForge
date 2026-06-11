## ADDED Requirements

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
