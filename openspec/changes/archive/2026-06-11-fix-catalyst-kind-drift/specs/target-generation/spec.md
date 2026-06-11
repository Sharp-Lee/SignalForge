## MODIFIED Requirements

### Requirement: Contracted Target Assembly And Persistence

Target generation MUST assemble candidates into `target-contract` records and persist them only through `ContractStore.add_target()`. It MUST include separate `logic_score` and `buy_point`, `target_market`, catalysts, exit triggers, `priced_in`, system-stamped company `name`, and linked thesis ids. It MUST NOT write directly to target storage or bypass `target-contract` validation. Model-authored company names MUST NOT be used when assembling targets. Target ids MUST be system-derived from the candidate symbol and thesis id; model-authored candidate ids MUST NOT be used as persisted target ids. When assembling catalysts or exit triggers, optional keys with `null`/`None` values MUST be omitted before persistence so proposal-layer nullable metadata remains compatible with target-contract optional string fields.

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

#### Scenario: Null catalyst metadata is omitted
- **WHEN** a candidate catalyst includes `kind: null` or `value: null` with a non-empty description
- **THEN** the persisted target catalyst omits those null optional keys and remains valid under `target-contract`

#### Scenario: Non-null catalyst metadata is preserved
- **WHEN** a candidate catalyst includes a non-null `kind` or `value`
- **THEN** the persisted target catalyst keeps those fields unchanged
