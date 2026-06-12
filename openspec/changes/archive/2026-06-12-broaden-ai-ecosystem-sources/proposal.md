## Why

SignalForge's source set needs to cover the full AI ecosystem, not only server hardware and semiconductors. AI infrastructure signals now commonly transmit through data centers, power grids, energy storage, cooling, and software/platform adoption, so capture must include those domains before analysis can find the right cross-market thesis.

Live verification also showed that several high-value RSS feeds reject the default Python urllib user agent but work with a normal browser user agent. Fixing that at the fetcher boundary unlocks better sources without changing analysis or target contracts.

## What Changes

- Remove the unused `add-openbb-research-adapter` change directory. It was never implemented and conflicts with the current source-first direction.
- Update `RssHttpFetcher` default HTTP transport to send a browser-like User-Agent.
- Broaden the committed RSS source set across AI ecosystem domains:
  - hardware / semiconductor;
  - power / energy / data-center infrastructure;
  - AI technology / software.
- Add source `domain` metadata while keeping source configuration backward-compatible.
- Keep dead or parser-incompatible candidate feeds out of the enabled default set.
- Expand the cheap top-K signal scorer so power, energy, grid, data-center, cooling, and AI-software signals are less likely to be starved by a hardware-only keyword set.

## Capabilities

### New Capabilities

### Modified Capabilities
- `source-ingestion`: RSS HTTP fetchers use browser-like request headers while preserving injectable transport tests.
- `source-feed-set`: default source configuration expands from a narrow semiconductor set to verified AI ecosystem coverage with domain metadata.
- `capture-analyze-flow`: cheap cluster scoring recognizes broader AI ecosystem infrastructure terms.

## Impact

- Affected code:
  - `source_ingestion/fetchers/rss.py`
  - `source_ingestion/feed_config.py`
  - `config/rss_sources.example.json`
  - `pipeline_orchestration/core.py`
  - tests for RSS fetcher, source config, and scoring behavior
- Affected OpenSpec:
  - new change `broaden-ai-ecosystem-sources`
  - removal of unimplemented change `add-openbb-research-adapter`
- No changes to analysis prompts, target generation, contracts, digest rendering, market data, or scheduled run mechanics.
