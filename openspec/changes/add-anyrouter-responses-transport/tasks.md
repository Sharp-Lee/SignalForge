## 1. Planning

- [x] 1.1 Validate `add-anyrouter-responses-transport` planning artifacts with OpenSpec strict mode

## 2. Transport Implementation

- [x] 2.1 Add `ResponsesAPICompletion` implementing `Completion`
- [x] 2.2 Add schema and object JSON modes for Responses API
- [x] 2.3 Parse `output_text` and nested output content into JSON dicts
- [x] 2.4 Convert incomplete/failed/missing/bad/non-object output into `LlmProviderError`
- [x] 2.5 Record usage into `UsageRecord`

## 3. Integration

- [x] 3.1 Export `ResponsesAPICompletion`
- [x] 3.2 Add `RELAY_FORMAT=responses` support to `scripts/run_live.py`

## 4. Tests And Verification

- [x] 4.1 Add fake Responses client schema-mode test
- [x] 4.2 Add object-mode prompt schema assertion
- [x] 4.3 Add error tests for incomplete, failed, bad JSON, non-object JSON, and missing text
- [x] 4.4 Add lazy client test
- [x] 4.5 Run `pytest tests/ -x -q`
- [x] 4.6 Run `openspec validate add-anyrouter-responses-transport --strict`
