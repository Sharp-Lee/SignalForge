## 1. Provider Role

- [x] 1.1 Add investment reasoning schema export to `llm_provider`.
- [x] 1.2 Add investment reasoning prompt and user prompt rendering.
- [x] 1.3 Add provider enforcement that wraps `validate_investment_reasoning_audit()` in `LlmProviderError`.
- [x] 1.4 Add drift/all-required tests for the new role schema.

## 2. Analysis Orchestration

- [x] 2.1 Add `AnalysisSkipped` or equivalent typed skip for weak/rejected audits.
- [x] 2.2 Run `investment_reasoning` before free generation in `analyze()`.
- [x] 2.3 Include accepted audit in `AnalysisResult` and thesis metadata without changing free-form body semantics.
- [x] 2.4 Ensure weak/rejected audits do not call free generation, completeness critique, adversarial review, or `store.add_thesis()`.

## 3. Pending Flow

- [x] 3.1 Add terminal counts/states for `skipped_weak_logic` and `skipped_rejected_logic`.
- [x] 3.2 Update `analyze_pending()` to mark weak/rejected clusters terminal instead of using retry failure attempts.
- [x] 3.3 Preserve existing retry behavior for real analysis/provider exceptions.

## 4. Tests

- [x] 4.1 Add provider tests for accepted audit, hallucinated source id, invalid target gate, and prompt content.
- [x] 4.2 Add analysis tests for accepted audit continuing and weak/rejected audit stopping before free generation.
- [x] 4.3 Add pipeline tests proving weak/rejected clusters are not retried and do not create targets.
- [x] 4.4 Run `python -m pytest tests/ -q`.
- [x] 4.5 Run `openspec validate apply-reasoning-skill-to-analysis --strict`.
