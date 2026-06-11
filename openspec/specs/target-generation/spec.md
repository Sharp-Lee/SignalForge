# target-generation Specification

## Purpose
TBD - created by archiving change add-target-generation. Update Purpose after archive.
## Requirements
### Requirement: Injectable Proposer And Price I/O

The target generation layer MUST call target reasoning through an injectable `TargetProposer` protocol and MUST obtain `price_change_since_signal` through an injectable price lookup. The target proposer MUST receive an explicit authoritative symbol universe mapping from symbol to company name. Tests MUST use offline stubs and MUST NOT call a real LLM provider, market data source, external network, or require API keys.

#### Scenario: Offline proposer and price stubs drive generation
- **WHEN** target generation runs in tests
- **THEN** candidate targets and price movement come from injected stubs only

#### Scenario: Production price provider remains injected
- **WHEN** live pipeline needs real A-share prices
- **THEN** it injects a real `PriceLookup` implementation without changing target generation's core assembly logic

#### Scenario: Symbol universe includes authoritative names
- **WHEN** an LLM target proposer is constructed
- **THEN** its `symbol_universe` is a mapping from allowed symbol to authoritative company name rather than only a set of symbols

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

### Requirement: Confirmed Thesis Linkage

Generated targets MUST link only to confirmed theses. Draft or unconfirmed theses MUST NOT support generated targets, and target generation MUST rely on `ContractStore.add_target()` to enforce the canonical confirmed-thesis check.

#### Scenario: Draft thesis cannot support target
- **WHEN** target generation attempts to persist a target linked to a draft thesis
- **THEN** `ContractStore.add_target()` rejects the target

#### Scenario: Target links back to thesis
- **WHEN** a target is generated from a confirmed thesis
- **THEN** its `thesis_ids` includes the confirmed thesis id

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

### Requirement: Minimal MVP Boundaries

Target generation MUST NOT implement production LLM calls, dynamic top-N thresholds, target state transition policy, or feedback calibration in this change. Real A-share market data and real A-share universe construction MUST remain outside target generation core and enter only through the existing injectable `PriceLookup` and symbol-universe inputs.

#### Scenario: Target generation does not calibrate feedback
- **WHEN** target generation successfully creates a watch target
- **THEN** no calibration signal or feedback score is generated by this capability

#### Scenario: Real prices are provided by market data layer
- **WHEN** live pipeline runs with real market data enabled
- **THEN** target generation receives real `price_change_since_signal` values through the injected price lookup and does not fetch market data itself

### Requirement: Live Pipeline Uses Real Market Data By Default

The live pipeline harness SHALL use a provider-stamped A-share universe and real price lookup by default for `--pipeline`, while retaining an explicit stub-market-data mode for offline smoke runs.

#### Scenario: Real market data pipeline output
- **WHEN** `scripts/run_live.py --pipeline` runs without stub-market-data mode
- **THEN** output labels the price layer as `REAL`, identifies the universe source, and target `priced_in.price_change_since_signal` values come from the real price lookup

#### Scenario: Explicit stub mode remains available
- **WHEN** `scripts/run_live.py --pipeline --stub-market-data` runs
- **THEN** the harness uses the test fixture universe and `StubPriceLookup` and labels the price layer as `STUB`

