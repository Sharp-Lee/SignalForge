## Why

The current target-generation path can force-fit weak theses into the full A-share universe, producing noisy watchlist targets that pass structural contracts but fail the Micron-style relevance test. The system needs a grounded relevance gate before target generation: a thesis must first match a curated chokepoint node before any node-owned A-share candidates are considered.

## What Changes

- Add a chokepoint relevance matcher that evaluates a confirmed thesis against fixed, curated, screen-passing chokepoint-map nodes.
- Add provider prompt/schema/enforcement for the matcher: model output is `{matched:[{node, reason}]}`, node ids must come from the supplied curated node list, reasons must be non-empty Chinese prose, and hallucinated nodes fail closed.
- Add a compact `curated_nodes()` helper to `market_data.chokepoint_map`.
- Wire an injectable matcher into pipeline target generation. If a matcher is present and a thesis matches no chokepoint node, the pipeline skips target generation for that thesis. If matcher fails, the pipeline records an error and skips targets.
- Restrict target generation to the union of matched node A-share symbols when a matcher is enabled.
- Preserve backward compatibility: `matcher=None` keeps the existing target-generation behavior.

## Capabilities

### New Capabilities

- `chokepoint-relevance-gate`: validates thesis-to-curated-node relevance before target generation and limits target universe to matched nodes.

### Modified Capabilities

- `chokepoint-map`: exposes compact curated screen-passing node records for machine matching.
- `llm-provider`: adds the chokepoint matcher prompt, schema, and enforcement discipline.
- `pipeline-orchestration`: optionally applies the chokepoint relevance gate before target generation while preserving old behavior when no matcher is injected.

## Impact

- Affected code: `market_data/chokepoint_map.py`, `llm_provider/*`, `pipeline_orchestration/core.py`, a narrow optional metadata pass-through in `target_generation/core.py`, `scripts/run_live.py`, and offline tests.
- No database schema migration is required.
- No changes to thesis/target canonical contracts, source ingestion, digest generation, or publication.
- Live behavior changes only when a matcher is injected by the operation harness.
