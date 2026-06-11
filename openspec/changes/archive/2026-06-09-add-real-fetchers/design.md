## Context

`source-ingestion` now has an Adapter protocol, fixture-backed adapters, cursor storage, and a one-shot runner. All fetchers are still fixtures. This change adds real fetcher implementations for the two MVP sources: RSS/Atom over HTTP and local `last30days.py --agent --emit=json` via subprocess.

The key constraint is testability: production may use real HTTP/subprocess transports, but tests must inject stub or recorded transports and remain offline.

## Goals / Non-Goals

**Goals:**
- Add injectable HTTP transport for RSS/Atom feed fetching.
- Add injectable subprocess transport for `last30days.py --agent`.
- Make RSS/Atom fetchers cursor-driven so they return only new raw items, not merely rely on downstream dedup.
- Make last30days executable with the real topic-query CLI shape, while relying on downstream dedup for repeated topic research.
- Harden the runner so fetch-level and normalize-level failures are captured as source errors and do not abort the whole ingestion run.
- Keep all normalized signals flowing through existing Adapters and `ContractStore.add_signal()`.

**Non-Goals:**
- No live GDELT fetcher.
- No real market move or quote feed.
- No API keys or source configuration management.
- No scheduling policy.
- No test that hits the network or spawns a real process.

## Decisions

**D1 Transport injection is mandatory.** RSS fetchers receive an `http_get(url)` callable; last30days fetchers receive a `spawn(command)` callable. The default production transports can be thin wrappers around standard library APIs, but tests use stubs only.

**D2 Real fetchers feed existing Adapters.** The RSS real fetcher returns raw RSS/Atom-shaped items for `RssAtomAdapter`; the last30days real fetcher returns raw agent output for `Last30DaysAdapter`. Normalization stays in the adapters.

**D3 RSS cursor filtering is published-time high-water.** RSS/Atom cursor values represent the newest parsed `published_at` time processed in the previous successful run. Filtering is order-independent so newest-first feeds do not drop new entries. RSS dates may be RFC822 or ISO8601.

**D4 last30days is a topic query, not a feed.** The fetcher accepts configured topic(s) and invokes `python3 <script> <topic> --agent --emit=json`. It does not pass `--since` or any cursor flag that the real CLI does not support. Real JSON output is a report object, not a JSON array; `Last30DaysAdapter` extracts candidate source items from `items_by_source` and maps those items into `last30days_attention` signals. Repeated per-topic output is made idempotent by downstream `ContractStore.add_signal()` validation/dedup.

**D5 Fetch and normalize errors are runner-level source errors.** A fetcher can raise for network, parse, or subprocess failures. The runner catches fetch-level exceptions, records them on that source result, skips cursor update for that failed source, and continues to the next source. Adapter normalization can also fail on malformed raw items; the runner records that raw item as rejected/error and continues with the remaining items and sources.

**D6 XML parsing stays standard-library.** RSS/Atom parsing uses `xml.etree.ElementTree` and a small amount of namespace handling. A dedicated feed parser dependency is deferred until real feeds prove it is needed.

## Risks / Trade-offs

- RSS feeds vary in format. -> Support common RSS/Atom fields now and keep invalid entries droppable.
- last30days is not a pollable feed. -> Require configured topic(s), use the real topic CLI shape, parse real `--emit=json` report output, and rely on downstream dedup for repeats.
- Cursor semantics are source-specific. -> Keep cursor opaque to the runner and test each fetcher’s increment behavior.
- Skipping cursor updates on failed fetch may re-fetch data later. -> Prefer repeat work over losing data.

## Migration Plan

1. Add real fetcher delta spec and tasks.
2. Implement RSS/Atom HTTP fetcher and last30days subprocess fetcher with injectable transports.
3. Harden runner fetch and normalize error handling.
4. Add offline tests for cursor filtering and source failure isolation.
5. Validate OpenSpec and run pytest.

## Open Questions

- Exact production feed list is deferred.
- The production source for last30days topics is deferred; this change only requires explicit configured topic(s).
