## Why

Target generation currently uses a stub price layer and a hardcoded test symbol universe in `scripts/run_live.py`. That means live RSS -> analysis -> target runs can validate reasoning shape, but cannot validate whether proposed A-share targets are grounded in real company names and real post-signal price movement.

This change adds real A-share price lookup and a real A-share symbol universe behind the existing injectable seams so target generation can produce watchlist items with real `price_change_since_signal`.

## What Changes

- Add a market-data module with a production `PriceLookup` implementation for A-share prices.
- Add provider adapters behind a priority fallback chain:
  - `tushare` when `TUSHARE_TOKEN` is configured.
  - `akshare` when installed and reachable.
  - No raw direct HTTP adapter, per reviewer instruction.
- Add an authoritative A-share universe provider that stamps `{symbol: company_name}` from provider security lists instead of hand-written names.
- Wire `scripts/run_live.py --pipeline` to use the real price lookup and real universe by default, while keeping an explicit stub mode for offline smoke runs.
- Add offline tests with fake provider adapters for price lookup, fallback behavior, non-trading-day handling, missing-symbol failure, and universe stamping.

## Capabilities

### New Capabilities

- `market-data`: Real A-share quote/history lookup and authoritative symbol universe construction behind injectable provider adapters.

### Modified Capabilities

- `target-generation`: Production/live wiring uses real `PriceLookup` and authoritative symbol universe; tests still use stubs and no network.

## Impact

- Affected implementation:
  - new market-data / price module
  - new universe module/data builder
  - `scripts/run_live.py`
  - `tests/`
  - `requirements.txt` only if optional dependency declarations need tightening
- Explicitly not affected:
  - `target_generation.propose_targets()` / `_assemble_target()` core logic
  - `llm_provider/`
  - `analysis_orchestration/`
  - `news_contracts/`
  - dedup and signal clustering
- This change is not archived until reviewer approval, tests, OpenSpec strict validation, and live pipeline verification with real prices complete.
