## MODIFIED Requirements

### Requirement: Injectable Proposer And Price I/O

The target generation layer MUST call target reasoning through an injectable `TargetProposer` protocol and MUST obtain `price_change_since_signal` through an injectable price lookup. The target proposer MUST receive an explicit authoritative symbol universe mapping from symbol to company name. Tests MUST use offline stubs and MUST NOT call a real LLM provider, market data source, external network, or require API keys.

#### Scenario: Offline proposer and price stubs drive generation
- **WHEN** target generation runs in tests
- **THEN** candidate targets and price movement come from injected stubs only

#### Scenario: Production providers are outside this change
- **WHEN** a caller needs a real LLM proposer or real quote feed
- **THEN** this change exposes only protocol boundaries and does not require provider credentials

#### Scenario: Symbol universe includes authoritative names
- **WHEN** an LLM target proposer is constructed
- **THEN** its `symbol_universe` is a mapping from allowed symbol to authoritative company name rather than only a set of symbols

### Requirement: Contracted Target Assembly And Persistence

Target generation MUST assemble candidates into `target-contract` records and persist them only through `ContractStore.add_target()`. It MUST include separate `logic_score` and `buy_point`, `target_market`, catalysts, exit triggers, `priced_in`, system-stamped company `name`, and linked thesis ids. It MUST NOT write directly to target storage or bypass `target-contract` validation. Model-authored company names MUST NOT be used when assembling targets.

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

### Requirement: Empty Recommendation

When no candidate passes the MVP gates for eligibility, logic score, price lookup, catalysts, and exit triggers, target generation MUST return an empty recommendation with reasons. It MUST NOT invent a low-quality target merely to produce a list. Live harness verification MUST treat empty recommendation as a valid output only when no candidate qualifies; this change's DeepSeek hardening is complete only after a live `--targets` run persists at least one valid target.

#### Scenario: No qualified candidate returns empty recommendation
- **WHEN** all candidates are ineligible or malformed
- **THEN** target generation returns an empty recommendation with reasons and writes no target

#### Scenario: Empty catalyst candidate is skipped
- **WHEN** one candidate has empty `catalysts` or empty `exit_triggers`
- **THEN** target generation rejects that candidate with a reason and continues considering other candidates

#### Scenario: Empty recommendation does not create targets
- **WHEN** target generation returns an empty recommendation
- **THEN** the target table remains unchanged

#### Scenario: Live target smoke persists grounded target
- **WHEN** `scripts/run_live.py --author deepseek --targets` is run with a configured DeepSeek key
- **THEN** at least one target is persisted with a 0-100 `logic_score.score`, a universe-stamped `name`, and `validate_target.accepted = True`
