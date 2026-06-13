## Context

Target generation currently receives the full live A-share universe. Even after thesis-level reasoning gates, weak theses can still produce structurally valid but economically irrelevant targets because the model can choose from every allowed symbol. The chokepoint map now has curated, evidence-grounded nodes with node-owned A-share records and trigger strings; that map should become the relevance boundary for target generation.

The new gate sits after a confirmed thesis exists and before target generation. It asks a narrow question: is this thesis a real catalyst for any fixed curated chokepoint node? If yes, only the matched nodes' A-share symbols are passed to target generation. If no, no target is generated for the thesis.

## Goals / Non-Goals

**Goals:**
- Match confirmed theses against curated, `screen_pass=true` chokepoint-map nodes.
- Use an LLM matcher with strict schema and fail-closed node enforcement, not keyword matching.
- Limit target generation universe to matched node A-share records.
- Preserve old behavior when no matcher is injected.
- Make matcher failures produce no targets rather than falling back to full-universe target generation.

**Non-Goals:**
- Do not change triage selection.
- Do not change target-generation internals, target contracts, or canonical schemas.
- Do not change chokepoint map data.
- Do not update digest wording in this change.
- Do not connect chokepoint triggers to capture/triage.

## Decisions

### D1: The matcher uses only curated, screen-passing nodes

`market_data.chokepoint_map.curated_nodes()` returns compact node records containing `node`, `chokepoint_holder`, `china_position`, `triggers`, and compact `a_share` records. Seed nodes are excluded because they are historical allowlist entries, not grounded chokepoint decisions.

Alternative considered: match every node including seeds. Rejected because seeds exist only for backward-compatible migration and would recreate the old broad-universe behavior.

### D2: Matcher output is strict and node-closed

The matcher schema is `{matched:[{node, reason}]}`. Enforcement rejects malformed output, unknown node names, and empty reasons. Duplicate node names are de-duplicated in first occurrence order.

Alternative considered: tolerate unknown nodes as "suggestions". Rejected because invented nodes are precisely the hallucination surface this gate is meant to close.

### D3: Pipeline injection preserves backward compatibility

`analyze_pending()` and `run_pipeline()` gain an optional `chokepoint_matcher=None`. When absent, target generation calls `propose_targets()` exactly as before. Existing tests and manual code paths continue to work.

When present:
1. The pipeline calls `matcher.match(thesis, signals=cluster.signals, nodes=curated_nodes())`.
2. If matched nodes are empty, target generation is skipped and the thesis is kept.
3. If the matcher raises, a `PipelineError(stage="chokepoint-match", unit=thesis_id, ...)` is recorded and target generation is skipped.
4. If nodes match, target generation receives a temporary proposer constrained to the union of the matched nodes' A-share symbols.

### D4: Restriction is implemented at the provider universe boundary

The existing `LlmTargetProposer` already enforces symbols against its own `symbol_universe`. The pipeline should not reimplement target validation. Instead, for matched nodes the pipeline narrows the proposer universe before calling `propose_targets()`.

For `LlmTargetProposer`, the pipeline can create a narrowed proposer of the same class with the same transport, system prompt, and max token budget. For other proposers, the pipeline wraps the proposer and filters/stamps candidates to the matched node universe. This avoids changing the target-generation protocol.

### D5: Node metadata does not change canonical thesis shape

The canonical thesis and target contracts are not changed. The current target schema allows additional properties, so stored targets can carry local context fields such as `chokepoint_node`, `chokepoint_holder`, and `chokepoint_reason`. The pipeline injects those fields into candidates after node matching; target assembly only preserves those system-owned optional fields. The thesis schema does not define `chokepoint_nodes`, and analysis persists the thesis before matching, so thesis/node status is recorded in `PipelineResult` rather than by mutating the persisted thesis contract.

## Risks / Trade-offs

- [Risk] A true catalyst may be missed by the matcher. -> Mitigation: fail-closed is intentional; no-target is recoverable, forced false target is worse.
- [Risk] Narrowing requires proposer-specific handling. -> Mitigation: implement explicit narrowing for `LlmTargetProposer`, keep `matcher=None` legacy behavior, and use stub/fake proposers in tests for deterministic paths.
- [Risk] Node metadata storage could drift from contracts. -> Mitigation: do not change canonical contracts; keep metadata in pipeline result unless existing target payload accepts it.
- [Risk] Live quality depends on current curated map coverage. -> Mitigation: only curated nodes are matched; missing domains should produce no target until the map is extended.

## Migration Plan

1. Add `curated_nodes()` to `market_data.chokepoint_map`.
2. Add prompt/schema/enforcement and `LlmChokepointMatcher`.
3. Add optional pipeline injection and fail-closed target-stage behavior.
4. Wire `run_live.py` to construct the matcher for live DeepSeek runs.
5. Add offline tests for valid match, no match, matcher failure, enforcement errors, and legacy `matcher=None`.
