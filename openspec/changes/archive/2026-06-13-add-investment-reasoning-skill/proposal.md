## Why

The taxonomy now defines what kinds of investment logic exist, but the system still lacks a standard reasoning artifact for applying those logic types to a concrete signal. Without a contract for this reasoning audit, future prompt/runtime work can drift back into either free-form vague narrative or mechanical graph-triggered stock output.

## What Changes

- Add an `investment-reasoning-skill` capability that defines and implements a structured reasoning audit for a signal or signal cluster.
- Define the audit shape: primary logic, optional secondary logic, evidence status, premise validation, upward validation, transmission chain, downstream decomposition, chokepoint candidates, missing evidence, disconfirming evidence, target-search decision, and public caveat.
- Require the reasoning audit to be advisory metadata: it MUST guide analysis and review, but MUST NOT replace the free-form thesis body or directly create targets.
- Define fail-closed states so weak or rejected logic does not imply target generation.
- Add a pure Python schema/validator module and offline tests. Runtime wiring into `analysis_orchestration`, LLM prompts/schemas, storage schema changes, target generation, and digest rendering remain future changes.

## Capabilities

### New Capabilities

- `investment-reasoning-skill`: Contract for a taxonomy-aware reasoning audit that turns signal facts into a validated investment logic chain before chokepoint or target mapping.

### Modified Capabilities

None.

## Impact

- Adds OpenSpec artifacts for a new reasoning-skill capability.
- Adds a new `investment_reasoning` module containing canonical taxonomy values, JSON Schema, and fail-closed audit validation.
- Does not change prompts, existing schemas, persisted data, dependencies, scheduled jobs, or existing runtime behavior in this proposal.
- Future changes can implement the audit as LLM provider schema, analysis metadata, storage, and digest display once this contract is reviewed.
