## ADDED Requirements

### Requirement: Versioned Chokepoint Map
The system SHALL provide a versioned chokepoint map document at `config/chokepoint_map.json`. The top-level document MUST contain `schema_version` and `nodes`. The initial schema version MUST be `0.1`.

#### Scenario: Map has version and nodes
- **WHEN** the chokepoint map is loaded
- **THEN** it contains `schema_version: "0.1"` and a `nodes` array

### Requirement: Seed And Curated Node Schema
The chokepoint map SHALL support `seed` and `curated` node forms through `curation_status`. A `seed` node MUST require `domain`, `curation_status`, and at least one `a_share` item with `code`. A `curated` node MUST require `branch`, `node`, `structure`, `chokepoint_holder`, `china_position`, `elasticity`, `triggers`, `evidence`, and `screen_pass`.

#### Scenario: Seed node accepts placeholder name
- **WHEN** a seed node contains an A-share code and an empty string name placeholder
- **THEN** the node is valid for the seed migration

#### Scenario: Curated node missing structure is rejected
- **WHEN** a curated node omits required curated fields such as `structure`
- **THEN** schema validation rejects the node

### Requirement: Seed Universe Migration
The chokepoint map SHALL migrate the existing 40 A-share symbols as `AI生态` seed nodes. The migrated seed symbols MUST preserve the current `DEFAULT_A_SHARE_ALLOWLIST` order exactly. Seed nodes MUST NOT set `screen_pass` to true because they have not yet been re-screened.

#### Scenario: Migrated codes preserve old order
- **WHEN** the loader derives universe codes from the seed map
- **THEN** the result is exactly equal to the previous 40-symbol allowlist including order

#### Scenario: Seed nodes do not claim screening
- **WHEN** a migrated seed node is inspected
- **THEN** it does not set `screen_pass: true`

### Requirement: Chokepoint Map Loader
The system SHALL provide a stdlib-only loader in `market_data.chokepoint_map`. The loader MUST expose `load_map()`, `universe_codes()`, `symbol_names()`, and `trigger_index()`. The loader MUST NOT import `market_data.core`.

#### Scenario: Loader derives universe codes
- **WHEN** `universe_codes()` is called
- **THEN** it returns included A-share codes in map appearance order with duplicate codes removed after first occurrence

#### Scenario: Loader returns snapshot names
- **WHEN** `symbol_names()` is called
- **THEN** it returns code-to-name values recorded in the map, including empty seed placeholders

#### Scenario: Trigger index is empty for seed-only map
- **WHEN** `trigger_index()` is called for the initial seed-only map
- **THEN** it returns an empty dictionary

### Requirement: Chokepoint Map SOP
The change SHALL document the chokepoint-map SOP: first-principles domain decomposition, evidence-grounded structure judgment, Micron-style filter, Tushare-stamped A-share selection, and structured map output with seed-to-curated lifecycle.

#### Scenario: SOP includes completion standards
- **WHEN** the design documentation is reviewed
- **THEN** each SOP stage includes a completion standard for future map-building work
