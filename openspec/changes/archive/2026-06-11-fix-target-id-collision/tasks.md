## 1. Regression Tests

- [x] 1.1 Add test proving repeated model candidate ids across different theses do not collide
- [x] 1.2 Add test proving duplicate symbols within one thesis are skipped with rejected reason
- [x] 1.3 Add test proving model candidate id is ignored in the persisted target id

## 2. Implementation

- [x] 2.1 Change `_assemble_target()` to always derive target id from `symbol|thesis_id`
- [x] 2.2 Add per-thesis accepted-symbol tracking in `propose_targets()`
- [x] 2.3 Preserve existing `store.add_target()` error propagation

## 3. Verification

- [x] 3.1 Run targeted target-generation tests
- [x] 3.2 Run full pytest suite
- [x] 3.3 Run `openspec validate fix-target-id-collision --strict`
- [x] 3.4 Run live pipeline gate and confirm no target id UNIQUE error
