## 1. OpenSpec Artifacts

- [x] 1.1 Add market-data capability delta spec for provider chain, source-date pricing, and universe stamping
- [x] 1.2 Modify target-generation delta spec for real market-data injection and live harness behavior

## 2. Test-First Coverage

- [x] 2.1 Add failing offline tests for scoped no-proxy restoration and provider fallback
- [x] 2.2 Add failing offline tests for source-signal date price-change calculation and fail-closed cases
- [x] 2.3 Add failing offline tests for provider-stamped universe and AkShare per-function failure resilience
- [x] 2.4 Add failing offline tests for live harness real/stub market-data wiring

## 3. Market Data Implementation

- [x] 3.1 Add market_data provider protocols, error types, scoped no-proxy wrapper, and provider chain
- [x] 3.2 Implement Tushare and AkShare providers behind injectable clients/imports
- [x] 3.3 Implement RealPriceLookup using ContractStore source `published_at`
- [x] 3.4 Implement reviewed A-share code allowlist and provider-stamped universe builder

## 4. Live Harness Wiring

- [x] 4.1 Wire scripts/run_live.py pipeline mode to real universe and RealPriceLookup by default
- [x] 4.2 Add explicit stub market-data mode and label pipeline output as REAL or STUB

## 5. Verification

- [x] 5.1 Run targeted market-data and harness tests
- [x] 5.2 Run full pytest suite
- [x] 5.3 Run openspec validate add-real-prices-and-universe --strict
- [x] 5.4 Run live pipeline with real DeepSeek, RSS, real universe, and real prices; capture redacted stdout
