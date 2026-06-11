## ADDED Requirements

### Requirement: Configurable RSS Feed Set

The system SHALL support a configurable RSS source list for live capture. Source configuration MUST include source id, source name, URL, enabled flag, and optional quality tier. Feed URLs MUST NOT be hard-coded as the only production source list.

#### Scenario: Source config builds adapters
- **WHEN** a source config file lists enabled RSS feeds
- **THEN** the operation layer can build RSS adapters for those feeds

#### Scenario: Disabled source is skipped
- **WHEN** a configured source has `enabled = false`
- **THEN** the capture path does not build or run an adapter for that source

### Requirement: Narrow Default Source Template

The committed example source list SHALL keep the first live set narrow: ServeTheHome, EE Times, SemiWiki, and EDN enabled. Broad high-volume feeds such as The Register, Tom's Hardware, and TechPowerUp MAY be present but MUST be disabled by default.

#### Scenario: Narrow defaults avoid high-volume sources
- **WHEN** the example source config is used without edits
- **THEN** broad high-volume sources are not enabled by default

### Requirement: Source Verification Boundary

Candidate sources SHALL be verified with the same RSS fetcher/parser used by the system before being enabled by default. Sources that currently fail HTTP, TLS, timeout, or XML parsing MUST remain disabled or absent from the default enabled set.

#### Scenario: Dead source is not enabled by default
- **WHEN** a candidate feed fails current fetcher verification
- **THEN** it is not enabled in the committed default source template
