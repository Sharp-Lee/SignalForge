## 1. Chokepoint Map Artifacts

- [x] 1.1 Add `config/chokepoint_map.json` with schema version `0.1` and the 40 existing A-share symbols as ordered `AI生态` seed nodes.
- [x] 1.2 Add a test-side JSON Schema fixture or helper that validates seed and curated node shapes, including curated `if/then` required fields.

## 2. Loader And Universe Compatibility

- [x] 2.1 Add stdlib-only `market_data/chokepoint_map.py` with `load_map()`, `universe_codes()`, `symbol_names()`, and `trigger_index()`.
- [x] 2.2 Refactor `market_data/universe.py` so `DEFAULT_A_SHARE_ALLOWLIST` derives from `chokepoint_map.universe_codes()` while preserving its public import path and list behavior.
- [x] 2.3 Ensure the loader avoids importing `market_data.core` and keeps runtime name stamping delegated to provider-based universe construction.

## 3. Offline Tests

- [x] 3.1 Add ordered snapshot tests proving `universe_codes()` and `DEFAULT_A_SHARE_ALLOWLIST` exactly match the old 40-symbol list.
- [x] 3.2 Add loader tests for `load_map()`, `symbol_names()`, `trigger_index()`, duplicate-preserving-order behavior, and clear invalid JSON errors.
- [x] 3.3 Add schema tests proving seed JSON is valid and malformed curated nodes are rejected.
- [x] 3.4 Add a compatibility test showing provider-stamped `build_default_universe()` names are not replaced by empty seed placeholders.

## 4. Verification

- [x] 4.1 Run targeted chokepoint/universe tests.
- [x] 4.2 Run `python -m pytest tests/ -q`.
- [x] 4.3 Run `openspec validate add-chokepoint-map-universe --strict`.
- [x] 4.4 Confirm the diff excludes `.local/`, keys, LLM calls, and runtime behavior changes outside the universe source refactor.
