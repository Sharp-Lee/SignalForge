## Why

The current analyze backlog can select terminal-product noise for deep analysis while missing true chokepoint catalyst signals until they expire. The existing chokepoint relevance gate prevents bad targets at the end of the pipeline, but it cannot rescue valuable pending clusters that triage never sends into analysis.

## What Changes

- Extend cluster triage with optional curated chokepoint-node context from the grounded chokepoint map.
- Keep the existing triage output schema unchanged: selected cluster ids plus Chinese reasons.
- Instruct triage to prefer clusters that materially affect a curated node's industry-level supply, demand, price, capacity, orders, domestic substitution, or competitive structure.
- Instruct triage to deprioritize single terminal-product launches, reviews, expo demos, consumer devices, NAS, mini-PCs, workstations, laptops, and one-off servers even when they mention advanced chips.
- Pass curated nodes into triage from the analyze path only when the selector supports that parameter.
- Preserve fallback behavior: no selector, no nodes, selector incompatibility, selector failure, invalid output, or empty output must keep the existing keyword fallback path.

No hard filtering is introduced at triage. Chokepoint matching remains a soft priority signal here; the existing target-stage chokepoint relevance gate remains the hard fail-closed filter.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `llm-provider`: cluster triage may receive optional grounded chokepoint-node context and must keep the existing output schema.
- `capture-analyze-flow`: pending analysis may pass curated chokepoint context into compatible triage selectors while preserving old behavior and keyword fallback.

## Impact

- Affected code:
  - `llm_provider/prompts.py`
  - `llm_provider/triage.py`
  - `pipeline_orchestration/core.py`
  - tests covering triage prompt injection, selector compatibility, and fallback.
- No new external dependencies.
- No change to target generation internals, chokepoint relevance gate behavior, digest generation, source configuration, or map content.
