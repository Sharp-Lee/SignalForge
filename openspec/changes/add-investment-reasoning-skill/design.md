## Context

The archived `investment-logic-taxonomy` capability defines the reasoning categories and the rule that a signal should have one primary investment logic plus optional secondary logic. The system now needs the next layer: a standard audit object that applies the taxonomy to a concrete signal or signal cluster.

The current analysis layer intentionally preserves free-form thesis generation. That remains correct. The reasoning skill should not force the final thesis body into a table. Instead, it should act as an audit trail and gating aid:

```text
signal facts
  -> reasoning audit
  -> free-form thesis body remains free
  -> chokepoint map consulted as memory
  -> target generation only if the logic is accepted
```

This change is still contract/design-first. It defines the audit structure and boundaries but does not wire it into prompts, storage, analysis, target generation, or digest rendering.

## Goals / Non-Goals

**Goals:**

- Define a canonical `InvestmentReasoningAudit` shape.
- Require exactly one `primary_logic_type` and optional `secondary_logic_types`.
- Require an `evidence_status` of `accepted`, `weak`, or `rejected`.
- Preserve the taxonomy's upward validation, transmission-chain, downstream decomposition, chokepoint-candidate, and falsification checks.
- Make weak/rejected logic fail closed: it can be recorded for study but must not imply target search.
- Keep the audit compatible with future use as optional thesis metadata or analysis-side output.

**Non-Goals:**

- Do not change `thesis-contract` or its JSON schema in this change.
- Do not change `analysis_orchestration`, `llm_provider`, `target_generation`, `daily-digest`, `chokepoint_map.json`, storage, or runtime behavior.
- Do not implement a new LLM prompt or provider schema yet.
- Do not require a rigid reasoning template inside the free-form thesis `body`.
- Do not select or mutate targets from the audit alone.

## Decisions

### D1. Reasoning audit is metadata, not thesis prose

The audit should be a structured companion to the analysis process. It may later be stored as optional thesis metadata or a separate analysis artifact, but it must not replace or constrain the free-form `body`.

Rationale: `thesis-contract` explicitly protects free-form generation. The audit should give the system a checklist and a record of what was validated, not turn the thesis into a fixed table.

### D2. Minimal audit shape

The recommended future shape is:

```json
{
  "source_signal_ids": ["sig-1"],
  "primary_logic_type": "supply_demand",
  "secondary_logic_types": ["margin_spread_repricing"],
  "evidence_status": "accepted",
  "premise": "HBM capacity tightness may indicate structurally high AI memory demand.",
  "upward_validation": [
    {
      "question": "Is terminal AI accelerator demand still expanding?",
      "answer": "Cloud capex and accelerator shipment signals support the premise.",
      "evidence": ["sig-1"],
      "status": "supported"
    }
  ],
  "transmission_chain": [
    "AI accelerator demand -> HBM content per accelerator -> HBM capacity tightness -> margin pressure/pricing power"
  ],
  "downstream_decomposition": [
    "Separate HBM makers, advanced packaging, TSV/test, equipment, and materials before looking for targets."
  ],
  "chokepoint_candidates": [
    {
      "node": "HBM advanced packaging",
      "reason": "Capacity and yield expansion can be slower than end demand."
    }
  ],
  "target_search_decision": {
    "status": "allowed",
    "reason": "Evidence is accepted and downstream bottleneck candidates are identified."
  },
  "missing_evidence": ["Customer-level HBM order duration"],
  "disconfirming_evidence": ["AI capex cut", "HBM price reversal"],
  "public_caveat": "This is a supply-demand watch item; it still depends on AI capex and HBM pricing staying firm."
}
```

This is intentionally smaller than a full research report. It captures the reasoning gate, not every detail of the thesis.

### D3. Evidence status gates target search

The audit uses three evidence states:

- `accepted`: enough hard evidence and transmission logic exists to proceed into deeper analysis and target search.
- `weak`: plausible but missing material evidence; can be tracked or sent back for more research.
- `rejected`: generic news, marketing language, missing economic transmission, or failed premise.

Only `accepted` may set `target_search_decision.status` to `allowed`. `weak` and `rejected` must set it to `not_ready` or `blocked`.

Rationale: this is the fail-closed guardrail that prevents "the model found a label, therefore emit stocks."

### D4. Taxonomy values are canonical

`primary_logic_type` and all `secondary_logic_types` must come from `investment-logic-taxonomy`. Unknown or invented logic labels should be rejected by future schema/enforce layers.

Rationale: invented labels silently destroy the taxonomy's value and make downstream behavior untestable.

### D5. Chokepoint candidates are candidates, not proof

The audit can list chokepoint candidates, but the map lookup remains a later step and the candidates are not themselves target recommendations.

Rationale: the graph is memory. It should narrow where to investigate, not substitute for source-backed reasoning.

### D6. Public caveats are part of the audit

Every audit should carry a `public_caveat` suitable for digest use. It should state what the logic depends on and what remains uncertain, using "research note / observation" language rather than recommendation language.

Rationale: digest output is public-facing and must avoid turning reasoning into a recommendation.

## Risks / Trade-offs

- [Audit becomes a rigid thesis template] -> Keep it metadata and explicitly preserve free-form thesis body.
- [Audit becomes too heavy] -> Keep the shape small and focus on the gating chain: premise, validation, transmission, decomposition, falsification.
- [Weak logic still leaks into targets] -> Require `target_search_decision.status` to be blocked/not-ready unless `evidence_status` is accepted.
- [LLM invents taxonomy labels] -> Future implementation should schema/enforce against canonical taxonomy values.
- [Digest overstates confidence] -> Carry `public_caveat`, `missing_evidence`, and `disconfirming_evidence`.

## Migration Plan

1. Review and approve this reasoning-audit contract.
2. Later change: add LLM provider schema/prompt for producing `InvestmentReasoningAudit` with offline tests.
3. Later change: wire the audit into analysis orchestration while preserving free-form thesis body.
4. Later change: persist the audit as optional thesis metadata or a separate analysis artifact.
5. Later change: allow target generation to receive accepted audits and map candidates as context, while retaining target-contract validation and empty-output behavior.
6. Later change: render digest cards that show the logic chain, missing evidence, and public caveat.

## Open Questions

- Should the audit eventually live inside thesis records as optional `investment_reasoning`, or in a separate table keyed by thesis/signal cluster?
- Should `weak` logic be included in digest as "研究观察" or excluded until accepted?
- Should chokepoint candidates reference node names only, or future stable node ids after the map schema evolves?
