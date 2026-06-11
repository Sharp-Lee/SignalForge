## 1. Planning

- [x] 1.1 Validate `add-target-generation` planning artifacts with OpenSpec strict mode

## 2. Protocols

- [x] 2.1 Create target generation module structure
- [x] 2.2 Define injectable `TargetProposer` protocol and stub proposer
- [x] 2.3 Define injectable price lookup protocol and stub lookup
- [x] 2.4 Leave production LLM and market data providers as explicit out-of-scope boundaries

## 3. Target Orchestration

- [x] 3.1 Implement candidate qualification gates for eligibility, logic score, catalysts, and exit triggers
- [x] 3.2 Assemble `target-contract` records with separated `logic_score` and `buy_point`
- [x] 3.3 Populate `priced_in.price_change_since_signal` from injected price lookup
- [x] 3.4 Force initial state to `watch` and link the supporting thesis id
- [x] 3.5 Persist targets only through `ContractStore.add_target()`

## 4. Empty Recommendation

- [x] 4.1 Return `create_empty_recommendation()` when no candidate qualifies
- [x] 4.2 Include rejection reasons in the empty recommendation
- [x] 4.3 Ensure empty recommendation writes no target rows

## 5. Tests And Verification

- [x] 5.1 Add offline test for confirmed thesis producing a valid watch target
- [x] 5.2 Add offline test that unfavorable buy point is not persisted as buy-zone
- [x] 5.3 Add offline test for empty recommendation when no candidate qualifies
- [x] 5.4 Add offline test that unconfirmed thesis linkage is rejected
- [x] 5.5 Run `python3 -m pytest -q`
- [x] 5.6 Run `openspec validate add-target-generation --strict`
