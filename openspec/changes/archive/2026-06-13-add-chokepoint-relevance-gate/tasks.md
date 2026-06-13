## 1. Map And Provider

- [x] 1.1 Add `curated_nodes()` to `market_data.chokepoint_map`.
- [x] 1.2 Add chokepoint matcher prompt and user prompt renderer.
- [x] 1.3 Add strict matcher schema and enforcement.
- [x] 1.4 Add `LlmChokepointMatcher` and exports.

## 2. Pipeline Wiring

- [x] 2.1 Add optional chokepoint matcher injection to `run_pipeline()` and `analyze_pending()`.
- [x] 2.2 Apply fail-closed matching before target generation.
- [x] 2.3 Restrict LLM target proposer universe to matched node A-share symbols.
- [x] 2.4 Attach matched node context to produced targets when enabled.
- [x] 2.5 Wire live DeepSeek matcher in `scripts/run_live.py`.

## 3. Tests And Validation

- [x] 3.1 Add offline tests for matcher enforcement.
- [x] 3.2 Add offline tests for curated node helper.
- [x] 3.3 Add offline pipeline tests for match, no-match, matcher failure, and `matcher=None` compatibility.
- [x] 3.4 Run full tests and `openspec validate add-chokepoint-relevance-gate --strict`.
