## MODIFIED Requirements

### Requirement: Contracted Target Assembly And Persistence

Target generation MUST assemble candidates into `target-contract` records and persist them only through `ContractStore.add_target()`. It MUST include separate `logic_score` and `buy_point`, `target_market`, catalysts, exit triggers, `priced_in`, system-stamped company `name`, and linked thesis ids. It MUST NOT write directly to target storage or bypass `target-contract` validation. Model-authored company names MUST NOT be used when assembling targets. Target ids MUST be system-derived from the candidate symbol and thesis id; model-authored candidate ids MUST NOT be used as persisted target ids.

#### Scenario: Confirmed thesis creates a watch target
- **WHEN** a confirmed thesis and qualified candidate are provided
- **THEN** target generation persists a `watch` target through `ContractStore.add_target()`

#### Scenario: Logic and buy point remain separate
- **WHEN** a candidate is assembled into a target
- **THEN** `logic_score` and `buy_point` are separate fields and no single total score is used

#### Scenario: Unfavorable buy point is not buy zone
- **WHEN** a candidate has an unfavorable buy point
- **THEN** target generation MUST NOT present it as `buy-zone` or `hold`

#### Scenario: Target name comes from universe
- **WHEN** a candidate is assembled into a target
- **THEN** the target `name` equals the authoritative company name mapped from the candidate symbol

#### Scenario: Model candidate id is ignored
- **WHEN** a candidate includes an `id` field such as `candidate-1`
- **THEN** the persisted target id is derived from the candidate symbol and thesis id

#### Scenario: Same model id across theses does not collide
- **WHEN** different confirmed theses receive candidates with the same model-authored id
- **THEN** target generation persists distinct target ids for each thesis

### Requirement: Empty Recommendation

When no candidate passes the MVP gates for eligibility, logic score, price lookup, catalysts, exit triggers, and per-thesis duplicate-symbol filtering, target generation MUST return an empty recommendation with reasons. It MUST NOT invent a low-quality target merely to produce a list. Live harness verification MUST treat empty recommendation as a valid output only when no candidate qualifies; this change's DeepSeek hardening is complete only after a live `--targets` run persists at least one valid target.

#### Scenario: No qualified candidate returns empty recommendation
- **WHEN** all candidates are ineligible or malformed
- **THEN** target generation returns an empty recommendation with reasons and writes no target

#### Scenario: Empty catalyst candidate is skipped
- **WHEN** one candidate has empty `catalysts` or empty `exit_triggers`
- **THEN** target generation rejects that candidate with a reason and continues considering other candidates

#### Scenario: Duplicate symbol in one thesis is skipped
- **WHEN** one target proposal contains multiple candidates for the same symbol
- **THEN** target generation persists only the first qualifying candidate for that symbol and records a duplicate-symbol rejected reason for later candidates

#### Scenario: Empty recommendation does not create targets
- **WHEN** target generation returns an empty recommendation
- **THEN** the target table remains unchanged

#### Scenario: Live target smoke persists grounded target
- **WHEN** `scripts/run_live.py --author deepseek --targets` is run with a configured DeepSeek key
- **THEN** at least one target is persisted with a 0-100 `logic_score.score`, a universe-stamped `name`, and `validate_target.accepted = True`
