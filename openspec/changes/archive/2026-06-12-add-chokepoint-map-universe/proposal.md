## Why

The A-share universe is currently a flat hand-maintained list of 40 symbols. The system needs a structured chokepoint-map foundation so future daily scanning can connect real-world signals to domain nodes and then to the most relevant A-share names, while this change keeps the existing runtime universe behavior unchanged.

## What Changes

- Add the chokepoint-map SOP for turning broad domains into first-principles chokepoint nodes and A-share mappings.
- Add a versioned `config/chokepoint_map.json` structure with `seed` and `curated` node forms.
- Migrate the existing 40 A-share symbols into `seed` nodes under the `AI生态` domain, preserving the current symbol order exactly.
- Add a stdlib-only `market_data.chokepoint_map` loader exposing map loading, ordered universe code derivation, display-name snapshots, and a trigger-index placeholder.
- Refactor `market_data.universe.DEFAULT_A_SHARE_ALLOWLIST` to derive from the chokepoint map while keeping the public import path and list semantics stable.
- Add offline tests for schema validity, loader behavior, ordered universe compatibility, and current target/name-stamp paths.

Non-goals:

- Do not connect triggers into triage.
- Do not change target generation or graph-based stock selection.
- Do not fill curated AI ecosystem data beyond seed nodes.
- Do not add other domains.
- Do not change digest copy or runtime provider-stamped naming behavior.

## Capabilities

### New Capabilities

- `chokepoint-map`: Versioned structured map, SOP, seed/curated schema, and loader interfaces for ordered universe derivation and future trigger indexing.

### Modified Capabilities

- `market-data`: The reviewed A-share allowlist is derived from the chokepoint map while provider-stamped runtime universe construction remains unchanged.

## Impact

- Affected files:
  - `config/chokepoint_map.json`
  - `market_data/chokepoint_map.py`
  - `market_data/universe.py`
  - tests covering the loader and market-data universe compatibility
  - OpenSpec change artifacts
- No runtime dependencies are added for the loader.
- `jsonschema` may be used in tests only; runtime loader validation stays lightweight and stdlib-only.
- Existing imports of `DEFAULT_A_SHARE_ALLOWLIST` remain stable.
