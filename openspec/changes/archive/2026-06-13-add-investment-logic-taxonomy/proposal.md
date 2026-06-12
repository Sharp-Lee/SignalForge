## Why

The system currently has a growing chokepoint map, but the user's actual workflow is a broader investment reasoning skill: a news item should first be classified by investment logic, then verified upward, decomposed downward, and only then mapped to chokepoints and targets. Without a shared taxonomy, future prompts and graph nodes can drift into generic "related stock" reasoning.

## What Changes

- Add a canonical investment-logic taxonomy covering the main narrative types the research system should recognize.
- Define one primary logic type plus optional secondary logic types as the future operating model, so classification remains a reasoning aid rather than a loose tag cloud.
- Define each logic type's selection criteria, upward validation questions, transmission-chain questions, downstream decomposition questions, rejection cases, minimum evidence thresholds, and falsification points.
- Document how the taxonomy relates to the chokepoint map: taxonomy explains why a signal matters; the map helps find where value may concentrate.
- Keep this change contract-only and documentation-only for now.
- Do not alter capture, triage, analysis, target generation, digest generation, market data, or chokepoint-map runtime behavior.

## Capabilities

### New Capabilities

- `investment-logic-taxonomy`: Canonical logic types and reasoning templates for classifying investment narratives before deeper analysis and target mapping.

### Modified Capabilities

None.

## Impact

- Adds OpenSpec artifacts for a new reasoning taxonomy capability.
- No code, prompts, schemas, runtime behavior, dependencies, scheduled jobs, or persisted data are changed in this proposal step.
- Future changes may apply this taxonomy to analysis prompts, chokepoint-map node metadata, target generation, and digest rendering after this taxonomy is reviewed.
