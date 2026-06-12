## MODIFIED Requirements

### Requirement: Provider-Stamped A-Share Universe

The system SHALL build the target symbol universe from a reviewed domain code allowlist derived from the chokepoint map plus provider security-list names. Tushare `stock_basic` names MUST be preferred when available; AkShare code-name rows MAY fill gaps. Displayed runtime company names MUST come from provider rows and MUST NOT be hand-written or taken from chokepoint-map seed placeholders.

#### Scenario: Tushare builds authoritative universe
- **WHEN** Tushare returns code/name rows for the reviewed chokepoint-map-derived allowlist
- **THEN** the universe maps allowed symbols to Tushare-stamped company names

#### Scenario: AkShare code-name failure does not break Tushare universe
- **WHEN** Tushare returns names but AkShare code-name lookup raises a network error
- **THEN** universe construction still succeeds from Tushare and records the AkShare failure as a skipped fallback

#### Scenario: Missing code is skipped with reason
- **WHEN** a reviewed allowlist code is missing from every provider security list
- **THEN** universe construction omits that code and records a reason instead of inventing a name

#### Scenario: Chokepoint map does not replace provider name stamping
- **WHEN** the chokepoint map contains empty seed name placeholders
- **THEN** runtime universe construction still uses provider-stamped names and does not display those placeholders as authoritative company names
