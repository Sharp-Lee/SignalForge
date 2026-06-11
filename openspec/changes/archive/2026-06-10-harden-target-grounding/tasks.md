## 1. Planning Gates

- [x] 1.1 Validate `harden-target-grounding` planning artifacts with OpenSpec strict mode
- [x] 1.2 Get reviewer decision on R4 candidate malformed handling before changing raise semantics

## 2. Provider Grounding

- [x] 2.1 Update target system and user prompts to require 0-100 integer `logic_score.score` with anchors and explicit ban on 1-10 scoring
- [x] 2.2 Remove model-authored `name` from `TARGET_PROPOSAL_SCHEMA`
- [x] 2.3 Change target `symbol_universe` handling from set of symbols to authoritative symbol-to-name mapping
- [x] 2.4 Stamp candidate `name` from the authoritative universe in `enforce_target_candidates`
- [x] 2.5 Keep out-of-universe symbols and invalid score ranges fail-closed with `LlmProviderError`

## 3. Target Generation Integration

- [x] 3.1 Update `LlmTargetProposer` typing and prompt input to pass authoritative universe mappings
- [x] 3.2 Preserve `_assemble_target()` behavior while ensuring candidate `name` is already system-stamped
- [x] 3.3 Apply the reviewer-approved R4 behavior for malformed candidates, or leave batch raise unchanged if reviewer rejects the split

## 4. Tests

- [x] 4.1 Update all tests from set-shaped `symbol_universe` to dict-shaped universe fixtures
- [x] 4.2 Add regression test proving model-output `name` is ignored or impossible and stamped from universe
- [x] 4.3 Add regression test proving target prompt contains 0-100 scale anchors and forbids 1-10 scoring
- [x] 4.4 Add regression test proving out-of-universe symbols still raise
- [x] 4.5 Update schema drift and all-required schema tests
- [x] 4.6 Add or update R4 regression coverage according to reviewer decision

## 5. Harness And Verification

- [x] 5.1 Update `scripts/run_live.py` target universe fixture to dict shape with authoritative names
- [x] 5.2 Run `python -m pytest tests/ -x -q`
- [x] 5.3 Run `openspec validate harden-target-grounding --strict`
- [x] 5.4 Run redacted DeepSeek live smoke: `python scripts/run_live.py --author deepseek --targets`
- [x] 5.5 Confirm live output shows 0-100 score, at least one persisted target, universe-stamped name, and `validate_target.accepted=True`
