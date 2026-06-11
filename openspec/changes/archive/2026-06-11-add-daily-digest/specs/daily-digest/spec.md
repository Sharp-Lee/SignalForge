## ADDED Requirements

### Requirement: Read-Only Daily Digest Generation

The system SHALL provide a daily digest generator that reads the persistent SQLite store without mutating it and writes both Markdown and inline-style HTML outputs for a selected date.

#### Scenario: Digest writes markdown and html
- **WHEN** `scripts/generate_digest.py --store PATH --date YYYY-MM-DD --out DIR` runs
- **THEN** it writes `DIR/YYYY-MM-DD.md` and `DIR/YYYY-MM-DD.html`

#### Scenario: Digest does not mutate store
- **WHEN** the digest generator runs against an existing store
- **THEN** thesis, target, and track record counts remain unchanged

### Requirement: Same-Day Thesis Selection

The digest SHALL include theses newly added on the selected date, using `track_record.created_at` as the selection timestamp.

#### Scenario: Same-day thesis appears
- **WHEN** a thesis has `track_record.created_at` on the selected date
- **THEN** the digest includes that thesis in the "今日研究观点" section

#### Scenario: Other-day thesis is excluded from daily thesis section
- **WHEN** a thesis has `track_record.created_at` outside the selected date
- **THEN** it is not listed as a same-day new thesis

### Requirement: Logic-Chain Digest Cards

The digest SHALL group same-day content by investment logic, showing the chain from source information to support logic, confirmed thesis, counterargument, and selected targets.

#### Scenario: Logic card shows source information
- **WHEN** a same-day thesis references source signals
- **THEN** the digest includes each signal title, source name, published time, and URL in that thesis card

#### Scenario: Logic card shows reasoning chain
- **WHEN** a same-day thesis has transmission path, body, and adversarial falsification
- **THEN** the digest includes world context, supporting logic, confirmed logic, and strongest counterargument sections

#### Scenario: Targets are scoped to the supporting logic
- **WHEN** targets link to a thesis through `thesis_ids`
- **THEN** only targets linked to that thesis are listed under that thesis card

### Requirement: Per-Logic Observation Object Summary

The digest SHALL include reader-facing observation-object fields under the logic that produced them: company name and code, logic relevance score, signal-since price change, priced-in risk, observation conditions from catalysts, and invalidation conditions from exit triggers. The digest MUST NOT render `buy_point.status` or label any observation object as a buy point, recommendation, target price, or suggested purchase.

#### Scenario: Observation object fields are rendered in Chinese
- **WHEN** a stored target contains logic score, price change, priced-in risk, catalysts, and exit triggers
- **THEN** the digest renders Chinese labels for logic relevance, signal-since price change, priced-in risk, observation conditions, and invalidation conditions

#### Scenario: Missing optional values do not fail generation
- **WHEN** optional target fields are absent or null
- **THEN** the digest skips or marks them as unavailable without failing

#### Scenario: Buy-point wording is not rendered
- **WHEN** a stored target contains `buy_point.status`
- **THEN** the digest does not render a buy-point label or translated buy-point status

### Requirement: Personal Research Framing

The digest SHALL include a prominent disclaimer and frame content as personal research notes rather than investment recommendations.

#### Scenario: Disclaimer appears in both formats
- **WHEN** a digest is generated
- **THEN** both Markdown and HTML include the required investment-risk disclaimer

#### Scenario: Recommendation wording is avoided
- **WHEN** watchlist targets are rendered
- **THEN** the output uses observation/research wording and does not use "建议买入" or "推荐"

### Requirement: Empty Digest

The digest generator SHALL produce a short valid digest when the store is missing, empty, or has no new theses for the selected date.

#### Scenario: Empty store generates no-new-content digest
- **WHEN** the store has no theses and no targets
- **THEN** the generator writes a digest stating "今日无新增"
