## 1. Prompt And Selector

- [x] 1.1 Extend cluster triage prompt rendering to accept optional compact chokepoint nodes and inject node-aware priority rules only when nodes are present.
- [x] 1.2 Extend `LlmClusterTriageSelector.select()` with optional `chokepoint_nodes` while preserving the existing schema and thinking policy.

## 2. Analyze Path Wiring

- [x] 2.1 Pass `curated_nodes()` into compatible triage selectors from the analyze path.
- [x] 2.2 Preserve legacy selectors and existing keyword fallback when node context is absent, unsupported, or triage fails.

## 3. Tests And Verification

- [x] 3.1 Add offline provider tests for chokepoint-aware triage prompt injection and legacy no-node payload behavior.
- [x] 3.2 Add offline analyze-path tests for compatible selector node context, legacy selector compatibility, and fallback preservation.
- [x] 3.3 Run full test suite and `openspec validate add-chokepoint-aware-triage --strict`.
