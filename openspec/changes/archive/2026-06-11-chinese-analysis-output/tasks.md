## 1. Planning

- [x] 1.1 Create proposal, design, and llm-provider delta spec
- [x] 1.2 Validate `chinese-analysis-output` with OpenSpec strict mode before implementation

## 2. Prompt Tests

- [x] 2.1 Add prompt test for Simplified Chinese system prompt instruction on all four roles
- [x] 2.2 Add prompt test for English enum-token guardrail in reasoner and target user prompts
- [x] 2.3 Verify the new prompt tests fail before implementation

## 3. Implementation

- [x] 3.1 Update `llm_provider/prompts.py` system prompts with Simplified Chinese prose instruction
- [x] 3.2 Update reasoner and target user prompt rules with Simplified Chinese prose instruction
- [x] 3.3 Preserve existing target score-scale prompt wording and all schema/enforcement behavior

## 4. Verification

- [x] 4.1 Run prompt tests
- [x] 4.2 Run `python -m pytest tests/ -q`
- [x] 4.3 Run `openspec validate chinese-analysis-output --strict`
- [x] 4.4 Run live DeepSeek pipeline and confirm Chinese prose plus English enum validity
- [x] 4.5 Generate a digest from real data and confirm a logic card is Chinese-readable
