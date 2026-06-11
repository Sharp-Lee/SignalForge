## Context

The canonical contracts are now in `openspec/specs/`, and `ContractStore.add_signal()` is the only accepted write path for persisted signals. The system still has no real ingestion layer: sources cannot be fetched, normalized, cursored, or run idempotently through the signal contract.

This change builds the first concrete layer of the architecture: ① global structural source intake and ①b reverse intake skeleton. It must stay small and avoid implementing downstream gate, analysis, target, feedback, or scheduling strategy.

## Goals / Non-Goals

**Goals:**
- Define a uniform Adapter protocol with `fetch(cursor)` and `normalize(raw_item)`.
- Keep network I/O injectable so tests run fully offline with fixtures.
- Reuse `source_cursors` for incremental, idempotent runs.
- Route every normalized signal through `ContractStore.add_signal()` so signal-contract validation and dedup remain the single gate.
- Provide reference adapters for RSS/Atom, GDELT-shaped fixture data, existing last30days output, and a market-move reverse-intake stub.
- Provide a thin runner that can execute one source or several sources once.

**Non-Goals:**
- No real network calls in tests.
- No production source coverage target.
- No real-time market feed.
- No three-layer scheduling policy.
- No changes to ② gate, ③ analysis, ④ targets, or ⑤ feedback logic.
- No new `market-event-contract`; market move intake remains signal-contract compliant.

## Decisions

**D1 Adapter protocol separates fetch and normalize.** Each adapter exposes `fetch(cursor)` for raw source retrieval and `normalize(raw_item)` for signal-contract records. This lets source-specific parsing change without touching persistence and lets tests inject raw fixtures without network.

**D2 Network I/O is a constructor dependency.** Adapters receive a fetcher callable or fixture provider. Built-in tests use fixture fetchers only. This prevents accidental external dependencies and keeps the source layer deterministic.

**D3 Cursor ownership is per source.** The runner reads and writes `source_cursors` by adapter `source_id`. Cursor values are opaque strings owned by each adapter. A run is idempotent because writes go through `ContractStore.add_signal()` and cursor updates happen after source processing.

**D4 Persistence reuses ContractStore.add_signal.** The ingestion layer must not duplicate schema validation, triage, or dedup. If a signal is invalid, duplicated, or triaged out, the runner records the rejection in its run result and continues.

**D5 Reference sources are deliberately fixture-shaped.** RSS/Atom and GDELT adapters parse common formats but do not fetch live URLs by themselves. GDELT is modeled as JSON fixture records so the adapter protocol is proven without committing to a live API.

**D6 Reverse intake is a stubbed source adapter.** Market move data is injected as fixture/stub records and normalized into `signal_origin = market_move` signals with `trigger_reason`. The existing signal-contract hard gate decides whether they are accepted.

**D7 The runner is a thin one-shot abstraction.** It runs adapters once and returns counts. It is intentionally not a scheduler. Future daily/event/weekly orchestration can call this runner.

## Risks / Trade-offs

- Source fixtures may be too simple compared with real feeds. -> Keep adapters small and add real-source hardening in later source-specific changes.
- Cursor semantics differ by source. -> Treat cursor as adapter-owned opaque state and test idempotency per adapter.
- RSS parsing in the standard library is limited. -> Support enough RSS/Atom structure for fixtures now; graduate to a dependency only when real feeds require it.
- Rejections could hide useful debugging data. -> Return run-level accepted/rejected counts and reasons without bypassing `ContractStore`.

## Migration Plan

1. Add source-ingestion spec and tasks.
2. Add adapter protocol, reference adapters, reverse-intake stub, and one-shot runner.
3. Add offline fixture tests for normalize, cursor idempotency, and market move hard gate.
4. Validate `add-source-ingestion` strictly.

## Open Questions

- Which live RSS feeds and GDELT endpoints should be enabled first is deferred to a source-selection change.
- Real market move source and thresholds are deferred to a market-intake change.
