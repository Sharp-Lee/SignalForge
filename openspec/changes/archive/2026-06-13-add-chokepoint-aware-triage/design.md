## Context

The pipeline now has three relevant safety layers:

- pending analysis uses one LLM triage call to choose which clusters enter deep analysis;
- confirmed theses pass through a fail-closed chokepoint relevance gate before target generation;
- target generation then proposes only within the matched node's A-share universe.

The target-stage gate stops hallucinated stock picking, but it runs too late to protect valuable pending clusters. If triage selects Dell/NAS/product-review noise and skips a real memory or optical-module catalyst, the valuable cluster can age into `skipped_stale` before it ever reaches analysis.

The chokepoint map already exposes `curated_nodes()` for grounded, screen-passing nodes. This change uses that map as context for the existing single triage call.

## Goals / Non-Goals

**Goals:**
- Add chokepoint-node context to LLM cluster triage when available.
- Prefer clusters that materially affect an existing curated node's industry-level supply, demand, price, capacity, orders, domestic substitution, or competitive structure.
- Deprioritize terminal-product noise such as laptops, workstations, mini-PCs, NAS, consumer electronics, single servers, reviews, and expo demos.
- Keep the triage output schema unchanged.
- Preserve old behavior when no nodes are supplied or when the selector does not support chokepoint context.
- Keep existing fallback to deterministic keyword top-K when triage fails or returns invalid/empty output.

**Non-Goals:**
- No new per-cluster LLM calls.
- No hard filtering before analysis.
- No change to the target-stage chokepoint relevance gate.
- No source pruning or RSS configuration changes.
- No digest, WeChat, market data, or chokepoint-map content changes.

## Decisions

### D1. Chokepoint context is prompt context, not schema

The triage role keeps the schema `{selected: [{cluster_id, reason}]}`. Curated nodes are injected into the user payload only when `chokepoint_nodes` is non-empty. Reasons may mention the matched node name, but no new structured field is required.

Rationale: This keeps archival and runtime compatibility. The action needed at this layer is ordering, not persistence of a formal node match. Formal node matching remains the target-stage gate.

### D2. Soft preference, not hard gate

Triage should prefer chokepoint catalysts and deprioritize product noise, but it must not drop every unmatched cluster. A thesis does not exist yet, and some valuable signals may not map cleanly to today's incomplete curated map.

Rationale: Hard filtering belongs after a confirmed thesis is available. The triage layer only decides where to spend limited analysis budget.

### D3. Product-noise rule is duplicated from the matcher prompt

The triage prompt repeats the hard-earned matcher rule: terminal-product launches/reviews/demos are not chokepoint catalysts merely because they mention Blackwell, RTX, AI PCs, or similar advanced chips.

Rationale: The failure mode is upstream of the matcher. Repeating the rule at triage prevents budget from being spent on signals that the matcher will later reject anyway.

### D4. Pipeline uses feature-compatible selector invocation

`analyze_pending` will pass `curated_nodes()` into `triage_selector.select()` only when the selector accepts a `chokepoint_nodes` keyword. Selectors that do not accept the parameter continue to receive the current argument set.

Rationale: Existing tests and alternate selectors should keep working. This also preserves the documented injectable seam.

### D5. Node loading failure should not become a pipeline outage

If chokepoint nodes cannot be loaded for triage context, the selector should be called without nodes and existing fallback behavior should remain available.

Rationale: Chokepoint-aware triage is a ranking improvement. A local map issue should not prevent the analyze path from making progress through the pre-existing triage or keyword fallback.

## Risks / Trade-offs

- [Risk] Prompt context can become large as the curated map grows. → Mitigation: pass the compact curated-node view only, not evidence/caveats/full A-share metadata; keep the existing `triage_candidate_limit` unchanged.
- [Risk] Soft triage can still pick product noise if the model ignores instructions. → Mitigation: the target-stage chokepoint gate remains fail-closed, and live review will validate ranking quality.
- [Risk] Over-prioritizing the current map can hide emerging domains. → Mitigation: unmatched clusters are not hard-filtered and keyword fallback remains available.
- [Risk] Offline tests cannot prove model judgment. → Mitigation: tests verify prompt/context/enforcement and compatibility; reviewer will run the live DeepSeek gate against real pending clusters.

## Migration Plan

1. Add OpenSpec deltas for `llm-provider` and `capture-analyze-flow`.
2. Extend prompt rendering and `LlmClusterTriageSelector.select()` with optional `chokepoint_nodes`.
3. Pass curated nodes from `analyze_pending` to compatible selectors.
4. Add offline tests for prompt injection, legacy no-node behavior, selector compatibility, and fallback.
5. Run full tests and `openspec validate add-chokepoint-aware-triage --strict`.

## Open Questions

None for this change. Live ranking quality is intentionally left to the reviewer gate with real pending clusters and DeepSeek.
