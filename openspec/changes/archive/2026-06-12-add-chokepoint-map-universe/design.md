## Context

The current A-share target universe is a flat ordered list in `market_data/universe.py`:

```python
DEFAULT_A_SHARE_ALLOWLIST = [...]
```

Runtime universe construction is already provider-stamped: `build_default_universe(provider_chain)` takes the reviewed code allowlist and obtains company names from Tushare first, with AkShare as fallback. That name-stamp behavior is correct and must remain unchanged.

This change adds the first durable structure for the chokepoint-map system. It does not yet make the daily pipeline scan triggers or select targets from graph nodes. It only creates the reusable map format, migrates the existing 40 symbols as seed entries, and derives the existing allowlist from that map with zero behavior change.

## Goals / Non-Goals

**Goals:**

- Document the chokepoint-map SOP and lifecycle.
- Add a versioned `config/chokepoint_map.json` with `seed` and `curated` node shapes.
- Migrate the existing 40 symbols into `seed` nodes under `AI生态`, preserving order exactly.
- Add a stdlib-only loader in `market_data/chokepoint_map.py`.
- Keep `DEFAULT_A_SHARE_ALLOWLIST` import path and list behavior stable.
- Keep runtime provider-stamped names as the authoritative name source.
- Add offline tests for schema shape, loader behavior, and exact universe compatibility.

**Non-Goals:**

- Do not connect triggers into LLM triage.
- Do not change target generation or graph-based stock selection.
- Do not fill curated AI ecosystem data beyond seed nodes.
- Do not add other domains.
- Do not change digest wording.
- Do not change runtime market-data provider behavior.

## Decisions

### D1. Use one versioned map with seed and curated node forms

`config/chokepoint_map.json` will use:

```json
{
  "schema_version": "0.1",
  "nodes": []
}
```

Each node has `curation_status`:

- `seed`: a historical symbol seed that has not yet gone through chokepoint screening.
- `curated`: a fully screened chokepoint node with structure, China position, elasticity, triggers, evidence, and `screen_pass`.

The JSON Schema uses conditional validation:

- `seed` requires only `domain`, `curation_status`, and `a_share` with at least one `code`.
- `curated` requires `branch`, `node`, `structure`, `chokepoint_holder`, `china_position`, `elasticity`, `triggers`, `evidence`, and `screen_pass`.

Rationale: the existing 40 symbols are an allowlist seed, not a validated chokepoint graph. Forcing fake structure values would create false semantics. The lifecycle is explicit: `seed -> rescreen -> curated(screen_pass=true|false)`.

### D2. Seed migration preserves order and avoids fake names

The 40 current symbols will be migrated as one seed node per symbol:

```json
{
  "domain": "AI生态",
  "curation_status": "seed",
  "a_share": [{"code": "300308.SZ", "name": ""}]
}
```

Names stay empty in this change. The user will later fill Tushare-stamped names after review. Empty names are acceptable for seed records because runtime company names still come from providers.

### D3. Loader is stdlib-only and avoids import cycles

`market_data/chokepoint_map.py` must not import `market_data.core`. The dependency direction stays:

```text
market_data.core -> market_data.universe -> market_data.chokepoint_map
```

The loader exposes:

- `load_map() -> dict`
- `universe_codes() -> list[str]`
- `symbol_names() -> dict[str, str]`
- `trigger_index() -> dict[str, list[str]]`

Runtime validation is lightweight and stdlib-only. Tests may use `jsonschema` if available in the environment, but the loader must not require it.

### D4. Universe derivation keeps runtime behavior unchanged

`universe_codes()` includes:

- all `seed` node `a_share[].code` values;
- all `curated` node `a_share[].code` values where `screen_pass is True`.

It preserves JSON appearance order and de-duplicates while preserving first occurrence.

`market_data/universe.py` will set:

```python
DEFAULT_A_SHARE_ALLOWLIST = universe_codes()
```

The exported name and import path remain stable. `build_default_universe(provider_chain)` still stamps names from provider rows.

### D5. `symbol_names()` is a snapshot interface, not authority

`symbol_names()` returns code-to-name strings recorded in the chokepoint map. In this seed migration those names are empty strings.

This interface is for display, map review, and future graph tools. It must not replace the runtime provider-stamped names used by `build_default_universe(provider_chain)`.

### D6. Trigger index shape is fixed but empty in v0

`trigger_index()` returns `{}` in this change because seed nodes have no curated `node` ids or triggers. The shape is fixed as `dict[node, list[str]]` for future trigger scanning.

## SOP

### S1. 领域拆解

Use first-principles decomposition until the domain is reduced to atomic needs. The decomposition must be MECE and based on "what is physically required", not copied from market sectors or index categories.

Completion standard:

- The domain tree covers the main physical or economic chain without obvious duplicate branches.
- Each leaf can be investigated as a chokepoint candidate.

### S2. 节点结构判定

Ground each node with web evidence. Decide whether the global structure is monopoly, oligopoly, or fragmented; identify who holds the chokepoint; and classify China's position as dominant, substitute, or absent.

Completion standard:

- The node has evidence sources.
- The holder and China position are explicit.
- Unknowns are written as caveats rather than guessed.

### S3. 美光测试

Keep only nodes that satisfy all three filters:

- oligopoly or chokepoint;
- profit elasticity is much greater than revenue elasticity;
- there is a clear machine-matchable trigger.

Cut commodity exposure, pure policy-control stories, and ordinary good news.

Completion standard:

- Every surviving node has `screen_pass=true`.
- Every rejected node has a clear caveat or `screen_pass=false`.

### S4. A股选股

For each passing node, select the purest A-share exposure. Code and name must be stamped from Tushare. Mark role, purity, and confidence. If there is no pure play, keep `a_share=[]` rather than forcing a name.

Completion standard:

- Every A-share record has a verified code-name pair.
- Purity and confidence are marked.
- No weak proxy is promoted as pure exposure.

### S5. 结构化出图

Write the node into the schema so it can be replayed, updated, and accumulated across domains. The universe is the union of A-share records from seed nodes and screen-passing curated nodes.

Completion standard:

- The node validates against schema.
- Triggers are machine-matchable strings.
- Evidence and caveats are preserved.
- Re-screening can move a seed to curated pass/fail without losing history.

## Risks / Trade-offs

- [Static map names accidentally become runtime authority] -> Document and test that provider-stamped runtime universe construction remains unchanged.
- [Schema too strict for seed migration] -> Use conditional seed/curated shapes rather than fake placeholders.
- [Import cycle between market-data modules] -> Keep loader stdlib-only and independent of `market_data.core`.
- [Order drift changes prompt/universe behavior] -> Test exact ordered equality against the old 40-symbol list.
- [Future curated false nodes leak into universe] -> `universe_codes()` includes curated nodes only when `screen_pass is True`.

## Migration Plan

1. Add `config/chokepoint_map.json` with the 40 seed symbols in current order.
2. Add `market_data/chokepoint_map.py` with lightweight validation and loader interfaces.
3. Refactor `market_data/universe.py` to derive the default allowlist from the loader.
4. Add offline tests for ordered compatibility, schema behavior, loader interfaces, and unchanged market-data name-stamp path.
5. Run full tests and `openspec validate add-chokepoint-map-universe --strict`.

Rollback is simple: restore `market_data/universe.py` to the flat list and remove the map loader/config.

## Open Questions

None. Seed names intentionally remain empty until the reviewer fills Tushare-stamped names.
