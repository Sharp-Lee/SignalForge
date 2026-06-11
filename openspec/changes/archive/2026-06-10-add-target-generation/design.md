## Context

The system can now ingest signals and orchestrate confirmed theses. `target-contract` already defines the hard constraints for watchlist targets: logic and entry must be separated, targets must link to confirmed theses, catalysts and exit triggers are required, and an empty recommendation is valid when nothing qualifies.

This change adds the target generation orchestration layer. It turns one confirmed thesis into zero or more watchlist targets by calling an injectable proposer, enriching candidates with an injectable price lookup, assembling `target-contract` records, and persisting only through `ContractStore.add_target()`.

## Goals / Non-Goals

**Goals:**
- Define a `TargetProposer` protocol whose reasoning I/O is injectable.
- Define a price lookup seam for `priced_in.price_change_since_signal`.
- Assemble candidates into `target-contract` records with `logic_score`, `buy_point`, `target_market`, catalysts, exit triggers, and `state=watch`.
- Persist targets only through `ContractStore.add_target()`.
- Return an explicit empty recommendation when no candidate qualifies.

**Non-Goals:**
- No production LLM provider.
- No real market data source.
- No dynamic top-N thresholding or ranking engine.
- No target state transition engine beyond initial `watch`.
- No feedback calibration.

## Decisions

**D1 TargetProposer is a protocol, not a provider.** The orchestration layer calls `proposer.propose(thesis)` and receives candidate dictionaries. Production LLM wiring is deferred; tests use deterministic stubs.

**D2 Price lookup is a separate injectable seam.** The proposer can reason about buy point quality, but measured `price_change_since_signal` comes from `price_lookup(symbol, thesis)`. The MVP uses stubs; real quote sources are a later change.

**D3 Initial state is always `watch`.** Even if a proposer suggests a more aggressive state, target generation creates observation-list entries, not trade instructions. Existing `target-contract` still prevents unfavorable buy points from entering `buy-zone` or `hold`.

**D4 Qualification is minimal and explicit.** A candidate must be marked `eligible=True`, meet a configurable minimum `logic_score`, and include catalysts and exit triggers. If none qualify, the orchestrator returns `create_empty_recommendation()` with reasons instead of forcing a low-quality target.

**D5 Persistence goes through `ContractStore`.** The orchestrator never writes target rows directly. `ContractStore.add_target()` remains the source of truth for confirmed-thesis linkage and target-contract validation.

## Risks / Trade-offs

- Proposer output may be malformed. -> Treat malformed candidates as rejected reasons and return an empty recommendation when no valid candidate remains.
- Price lookup can fail or be unavailable. -> Do not invent price movement; record a rejection reason and skip that candidate in this MVP.
- A fixed logic threshold is crude. -> Keep it configurable and defer dynamic thresholding to a later change.
- Watchlist generation may overproduce. -> MVP processes only candidates returned by the proposer and does not implement top-N expansion.

## Migration Plan

1. Add `target-generation` delta spec and tasks.
2. Implement proposer protocol, stub proposer, price lookup protocol, and orchestration entrypoint.
3. Add offline tests for confirmed thesis -> target, empty recommendation, buy-point discipline, and unconfirmed thesis rejection.
4. Validate with `openspec validate add-target-generation --strict` and `python3 -m pytest -q`.

## Open Questions

- Production target proposer prompts and provider choice are deferred.
- Real quote provider and price baselining rules are deferred.
- Dynamic ranking and human-decision learning are deferred.
