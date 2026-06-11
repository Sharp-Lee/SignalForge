## 1. Planning

- [x] 1.1 Validate `add-analysis-orchestration` planning artifacts with OpenSpec strict mode

## 2. Reasoner Protocol

- [x] 2.1 Create analysis orchestration module structure
- [x] 2.2 Define injectable `Reasoner` protocol and reasoner metadata
- [x] 2.3 Add deterministic stub reasoner for offline tests
- [x] 2.4 Leave production LLM provider as explicit out-of-scope stub boundary

## 3. Three-step Orchestration

- [x] 3.1 Implement free-generation call using the author reasoner
- [x] 3.2 Implement completeness critique call that records audit output without rewriting body
- [x] 3.3 Implement adversarial falsification call using an independent reviewer reasoner
- [x] 3.4 Assemble confirmed thesis fields, track record, confidence, and uncertainty inputs
- [x] 3.5 Persist through `ContractStore.add_thesis()` only

## 4. Failure Gates

- [x] 4.1 Reject author/reviewer instance id or persona equality before confirmation
- [x] 4.2 Ensure missing completeness critique cannot be reported as success
- [x] 4.3 Ensure missing adversarial review cannot be reported as success

## 5. Tests And Verification

- [x] 5.1 Add offline test for full three-step flow producing a confirmed thesis
- [x] 5.2 Add offline test that author equals reviewer cannot confirm
- [x] 5.3 Add offline tests that missing critique or missing adversarial review cannot confirm
- [x] 5.4 Run `python3 -m pytest -q`
- [x] 5.5 Run `openspec validate add-analysis-orchestration --strict`
