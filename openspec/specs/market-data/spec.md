# market-data Specification

## Purpose
TBD - created by archiving change add-real-prices-and-universe. Update Purpose after archive.
## Requirements
### Requirement: Provider Chain For A-Share Market Data

The system SHALL provide a real A-share market-data provider chain that tries Tushare first when `TUSHARE_TOKEN` is configured, then AkShare when installed, and otherwise fails closed. The system MUST NOT implement a direct raw HTTP market-data provider in this change. Provider calls MUST be injectable for tests and MUST run inside a scoped no-proxy context that is restored after each provider call.

#### Scenario: Tushare primary succeeds
- **WHEN** Tushare returns a security list and daily bars for a requested symbol
- **THEN** the provider chain returns Tushare-sourced names and prices without calling AkShare

#### Scenario: Tushare misses one symbol and AkShare fills it
- **WHEN** Tushare fails for one requested symbol but AkShare returns bars for that symbol
- **THEN** the provider chain uses AkShare for that symbol and continues processing the batch

#### Scenario: No provider succeeds
- **WHEN** no configured provider can return bars for a symbol
- **THEN** market data lookup raises a market-data error instead of returning stub data

#### Scenario: Scoped proxy bypass restores environment
- **WHEN** a provider call runs inside the scoped no-proxy context
- **THEN** proxy environment variables and `urllib.request.getproxies` are restored after the call completes or raises

### Requirement: Price Change Uses Persisted Source Signal Date

The real price lookup SHALL calculate `price_change_since_signal(symbol, thesis)` from persisted source signal timestamps. It MUST read the thesis `source_signal_ids`, load matching `signals.payload_json` records from `ContractStore`, use the earliest valid `source.published_at`, choose the first trading-day close on or after that date, choose the latest available numeric price or latest daily close, and return `(current_price - signal_close) / signal_close`.

#### Scenario: Non-trading signal date resolves forward
- **WHEN** the source signal date is a non-trading day and daily bars begin on the next trading day
- **THEN** price lookup uses that next trading day's close as the signal price

#### Scenario: Missing source signal fails closed
- **WHEN** the thesis has no source ids, a source id is not present in the store, or a source has no parseable `source.published_at`
- **THEN** price lookup raises a market-data error so target generation can skip the candidate

#### Scenario: Latest quote unavailable falls back to latest daily close
- **WHEN** the provider cannot return a verified numeric latest quote but daily bars contain a latest close
- **THEN** price lookup uses the latest daily close as the current price

### Requirement: Provider-Stamped A-Share Universe

The system SHALL build the target symbol universe from a reviewed domain code allowlist plus provider security-list names. Tushare `stock_basic` names MUST be preferred when available; AkShare code-name rows MAY fill gaps. Displayed company names MUST come from provider rows and MUST NOT be hand-written.

#### Scenario: Tushare builds authoritative universe
- **WHEN** Tushare returns code/name rows for the reviewed allowlist
- **THEN** the universe maps allowed symbols to Tushare-stamped company names

#### Scenario: AkShare code-name failure does not break Tushare universe
- **WHEN** Tushare returns names but AkShare code-name lookup raises a network error
- **THEN** universe construction still succeeds from Tushare and records the AkShare failure as a skipped fallback

#### Scenario: Missing code is skipped with reason
- **WHEN** a reviewed allowlist code is missing from every provider security list
- **THEN** universe construction omits that code and records a reason instead of inventing a name

