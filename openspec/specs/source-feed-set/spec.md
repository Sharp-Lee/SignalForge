# source-feed-set Specification

## Purpose
TBD - created by archiving change decouple-capture-analyze. Update Purpose after archive.
## Requirements
### Requirement: Configurable RSS Feed Set

The system SHALL support a configurable RSS source list for live capture. Source configuration MUST include source id, source name, URL, enabled flag, optional quality tier, and optional ecosystem domain. Feed URLs MUST NOT be hard-coded as the only production source list.

#### Scenario: Source config builds adapters
- **WHEN** a source config file lists enabled RSS feeds
- **THEN** the operation layer can build RSS adapters for those feeds

#### Scenario: Disabled source is skipped
- **WHEN** a configured source has `enabled = false`
- **THEN** the capture path does not build or run an adapter for that source

#### Scenario: Source config preserves domain metadata
- **WHEN** a source config entry includes an ecosystem domain
- **THEN** the loaded source config preserves that domain for review and downstream operations

### Requirement: Source Verification Boundary

Candidate sources SHALL be verified with the same RSS fetcher/parser used by the system before being enabled by default. Sources that currently fail HTTP, TLS, timeout, or XML parsing MUST remain disabled or absent from the default enabled set.

#### Scenario: Dead source is not enabled by default
- **WHEN** a candidate feed fails current fetcher verification
- **THEN** it is not enabled in the committed default source template

### Requirement: AI Ecosystem Default Source Coverage
The committed example source list SHALL enable a verified AI ecosystem source set spanning hardware/semiconductor, power/energy/data-center infrastructure, and AI technology/software. Each enabled source MUST include domain metadata and quality tier metadata.

#### Scenario: Default sources span AI ecosystem domains
- **WHEN** the example source config is loaded
- **THEN** enabled sources include at least one `hardware`, one `energy`, and one `ai_tech` source

#### Scenario: Enabled sources include quality and domain
- **WHEN** an example source is enabled
- **THEN** it has both a quality tier and an ecosystem domain

