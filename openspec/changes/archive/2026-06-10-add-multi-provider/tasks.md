## 1. Planning

- [x] 1.1 Validate `add-multi-provider` planning artifacts with OpenSpec strict mode

## 2. Transport Implementation

- [x] 2.1 Add `OpenAICompatibleCompletion` implementing `Completion`
- [x] 2.2 Add schema and object JSON modes
- [x] 2.3 Add OpenAI-compatible response parsing, finish-reason errors, JSON errors, and usage records
- [x] 2.4 Add lazy `openai.OpenAI` client construction with `base_url` and `api_key_env`
- [x] 2.5 Add optional `base_url` to `AnthropicCompletion`

## 3. Exports And Dependencies

- [x] 3.1 Export `OpenAICompatibleCompletion` from `llm_provider.__init__`
- [x] 3.2 Add `openai>=1.0.0` to requirements

## 4. Tests And Verification

- [x] 4.1 Add fake OpenAI-compatible client tests for schema mode round trip
- [x] 4.2 Add object mode prompt schema assertion
- [x] 4.3 Add error tests for length, content_filter, bad JSON, and non-object JSON
- [x] 4.4 Add lazy client test
- [x] 4.5 Verify existing stub transport round trips remain compatible
- [x] 4.6 Run `pytest tests/ -x -q`
- [x] 4.7 Run `openspec validate add-multi-provider --strict`
