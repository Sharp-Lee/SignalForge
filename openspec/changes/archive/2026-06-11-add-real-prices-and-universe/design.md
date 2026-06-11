## Context

`target_generation.PriceLookup` already defines the seam:

```python
price_change_since_signal(symbol, thesis) -> float
```

`propose_targets()` catches price lookup exceptions per candidate and records the reason, so real market-data failures can fail closed without crashing the full target-generation batch.

The live harness currently uses:

- `TARGET_SYMBOL_UNIVERSE`: a hardcoded test fixture.
- `StubPriceLookup`: fixed fake price moves.

That was enough to validate target contract shape, but not enough for real A-share pricing or authoritative company-name stamping.

The route originally requested a raw HTTP floor, but the latest instruction says "不要http". This design therefore excludes direct EastMoney/Sina/raw HTTP adapters. Provider libraries may use network internally, but system code will not implement a naked HTTP provider.

## Goals / Non-Goals

**Goals:**
- Provide a real A-share `PriceLookup` implementation behind the existing `target_generation.PriceLookup` seam.
- Use real provider-backed `{symbol: authoritative_name}` universe data instead of hand-written names.
- Keep all providers injectable and offline-testable.
- Let live pipeline use real prices and real universe by default.
- Fail closed when no real market-data provider is available.

**Non-Goals:**
- No direct raw HTTP adapter.
- No changes to `target_generation.propose_targets()` or `_assemble_target()`.
- No changes to `llm_provider`, `analysis_orchestration`, `news_contracts`, dedup, or signal clustering.
- No valuation model, no ranking model, no portfolio sizing.
- No target contract schema change.
- No caching database in this change unless tests reveal provider calls need a minimal in-memory cache.

## Decisions

### D1 Provider Chain

Use a priority provider chain:

1. `TushareProvider`
   - Enabled only when `TUSHARE_TOKEN` is present.
   - Uses `tushare.pro_api(token)` for A-share security list and daily bars.
   - Preferred because it is token-backed and less brittle than scrape-style public endpoints.
2. `AkshareProvider`
   - Enabled only when `akshare` is installed.
   - Uses `stock_info_a_code_name()` for authoritative code/name rows.
   - Uses the verified `stock_zh_a_daily(symbol="sz300308" / "sh600000")` daily-bar path for price history.
   - Do not use `stock_zh_a_hist()` for this change: R1 smoke showed that endpoint currently disconnects under the required no-proxy wrapper, while `stock_zh_a_daily()` succeeds.
3. No raw HTTP floor.
   - If Tushare is unavailable and AkShare is unavailable/unreachable, the real lookup raises a market-data error.
   - `propose_targets()` already catches this per candidate and records rejected reasons.

Provider calls must run inside a scoped no-proxy context:

- clear `http_proxy`, `https_proxy`, `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`, `all_proxy`;
- set `NO_PROXY="*"` and `no_proxy="*"`;
- patch `urllib.request.getproxies = lambda: {}`;
- restore the environment and `getproxies` immediately after the provider call.

This bypass is local to market-data providers only. It must not be applied globally because DeepSeek/LLM traffic is already known to work with the user's existing proxy environment.

Rationale: the user's latest instruction explicitly rejects a raw HTTP provider. A fake fallback would silently reintroduce stub pricing into live mode, so the correct no-provider behavior is fail closed.

### D2 Price Change Calculation

Use the earliest `source.published_at` among the thesis source signals as the signal date.

Implementation shape:

1. Construct `RealPriceLookup(store=ContractStore, provider_chain=...)`.
2. In `price_change_since_signal(symbol, thesis)`, read `thesis["source_signal_ids"]`.
3. Query `store.signals.payload_json` for those source signal ids.
4. Parse each signal payload's `source.published_at`.
5. Use the earliest valid published date as `signal_date`.

This intentionally does not use `thesis.track_record.verification_window.start`. That window is for outcome tracking, not market entry timing. If the thesis has no source ids, a source id is missing from the store, or no referenced signal has `source.published_at`, the lookup raises `MarketDataError` and the candidate is skipped by `propose_targets()`.

Calculation:

1. Fetch provider daily bars from `signal_date` through today.
2. Choose signal price as the first available trading day's close on or after `signal_date`.
   - This handles weekends and exchange holidays without looking backward before the signal date.
3. Choose current price:
   - Prefer a provider latest quote only if that provider exposes a verified numeric latest quote path.
   - Otherwise use the most recent available daily close.
4. Return `(current_price - signal_close) / signal_close`.

Failure behavior:

- Missing `source_signal_ids`: raise `MarketDataError`.
- Source id not found in `store.signals`: raise `MarketDataError`.
- Missing or unparsable `source.published_at`: raise `MarketDataError`.
- No bars on or after signal date: raise `MarketDataError`.
- Suspended/no latest quote: fall back to most recent daily close if present; otherwise raise.
- Unknown symbol or provider mismatch: raise.

`propose_targets()` will skip that candidate and record the exception string.

### D3 Universe Source

The universe must provide authoritative `{symbol: company_name}` and must not hand-type company names.

Recommended MVP:

1. Fetch a full A-share security list from the active provider:
   - Tushare: `stock_basic(..., fields="ts_code,symbol,name,market,industry,list_status")`.
   - AkShare: `stock_info_a_code_name()` rows containing `code` and `name`.
2. Build the domain universe from provider-returned rows.
3. For a focused 30-50 name AI-server / semiconductor / power / optical / PCB universe, use a reviewed code allowlist for scope, but every code must be validated against the provider security list and every displayed name must come from the provider row.

This means "which symbols are in the investment universe" can be a reviewed scope decision, but "what is the company name for this symbol" must be provider authoritative. If a code is missing from the provider security list, fail the universe build.

### D4 Live Harness Wiring

`scripts/run_live.py --pipeline` should use:

- real universe provider to construct `symbol_universe`;
- real price lookup for `price_change_since_signal`;
- explicit `--stub-market-data` or environment flag only for offline smoke mode.

Live output must clearly state:

```text
price layer = REAL
universe source = <provider>
```

## R1 Real Interface Evidence

Evidence collected on 2026-06-10 with a signal date of 2026-06-05 and end date of 2026-06-10.

Environment:

- `TUSHARE_TOKEN`: set in `~/.config/news-llm/keys.env` and loaded via `source`; token value was never printed.
- `tushare`: `1.4.24`.
- `akshare`: `1.18.30`.
- Market-data provider calls used the scoped no-proxy wrapper described in D1.

Tushare primary path succeeded:

| code | authoritative name | signal trade date | signal close | latest trade date | latest price | price_change_since_signal |
|---|---|---:|---:|---:|---:|---:|
| 300308.SZ | 中际旭创 | 20260605 | 1179.9900 | 20260610 | 1147.0000 | -0.027958 |
| 300502.SZ | 新易盛 | 20260605 | 748.0000 | 20260610 | 772.5000 | 0.032754 |
| 002463.SZ | 沪电股份 | 20260605 | 133.2200 | 20260610 | 130.6000 | -0.019667 |

AkShare fallback path succeeded using `stock_info_a_code_name()` plus `stock_zh_a_daily()`:

| code | authoritative name | AkShare symbol | signal trade date | signal close | latest trade date | latest price | price_change_since_signal |
|---|---|---|---:|---:|---:|---:|---:|
| 300308 | 中际旭创 | sz300308 | 20260605 | 1179.9900 | 20260610 | 1147.0000 | -0.027958 |
| 300502 | 新易盛 | sz300502 | 20260605 | 748.0000 | 20260610 | 772.5000 | 0.032754 |
| 002463 | 沪电股份 | sz002463 | 20260605 | 133.2200 | 20260610 | 130.6000 | -0.019667 |

AkShare endpoint note:

- `stock_info_a_code_name()` succeeded and returned 5526 code/name rows.
- `stock_zh_a_daily()` succeeded for all three symbols above.
- `stock_zh_a_hist()` failed under the same required no-proxy wrapper with `ConnectionError: Remote end closed connection without response`; it is intentionally excluded from this design.

R1 gate conclusion: live non-stub price evidence is now available for both the primary Tushare path and the AkShare fallback path, without adding a raw HTTP provider. Implementation should not start until the reviewer approves this design evidence.

## Risks / Trade-offs

- [Risk] Without raw HTTP, live price lookup depends on token-backed Tushare or AkShare reachability. -> Mitigation: fail closed and surface rejected reasons; do not silently fall back to stubs.
- [Risk] AkShare provider APIs can change column names or upstream endpoints can fail. -> Mitigation: adapter tests use fake frames for expected shapes; live smoke evidence picks the currently verified `stock_zh_a_daily()` path.
- [Risk] A reviewed symbol allowlist can drift. -> Mitigation: names are never stored by hand; every code is provider-validated at runtime/build time.
- [Risk] Source-signal date lookup now depends on store access. -> Mitigation: `RealPriceLookup` takes `store` explicitly and fails closed when a thesis cannot be traced to persisted source signals.

## Migration Plan After R1 Approval

1. Add market-data module with provider protocols, scoped no-proxy wrapper, Tushare provider, AkShare provider, provider chain, and `RealPriceLookup`.
2. Add universe module that builds provider-stamped A-share universe from a reviewed code allowlist plus active provider security list.
3. Add offline tests using fake providers/frames:
   - provider success;
   - fallback when preferred provider fails;
   - missing symbol;
   - non-trading-day date resolution;
   - suspended/missing latest quote fallback;
   - source-signal date lookup from `store.signals.payload_json`;
   - missing source id / missing `source.published_at` fail closed;
   - universe name stamping.
4. Wire `scripts/run_live.py --pipeline` to real price/universe by default with explicit stub override.
5. Run full tests and OpenSpec strict validation.
6. Run live pipeline with real DeepSeek, real RSS, real universe, and real price lookup.

## Open Questions

- R1 evidence is ready for reviewer approval. No specs, tasks, or implementation should be written until this gate is approved.
