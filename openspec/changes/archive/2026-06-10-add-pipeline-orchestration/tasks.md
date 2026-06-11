## 1. Planning

- [x] 1.1 Validate `add-pipeline-orchestration` planning artifacts with OpenSpec strict mode

## 2. Pipeline Module

- [x] 2.1 Create pipeline orchestration module structure
- [x] 2.2 Define `PipelineResult` and stage error structures
- [x] 2.3 Implement newly persisted signal selection for the current run
- [x] 2.4 Keep clustering and scheduling as explicit out-of-scope boundaries

## 3. Composition Flow

- [x] 3.1 Call `source_ingestion.runner.run_once` for ingestion
- [x] 3.2 Call `analysis_orchestration.analyze` for each trivial signal group
- [x] 3.3 Call `target_generation.propose_targets` for each generated thesis
- [x] 3.4 Aggregate ingestion counts, theses, targets, empty recommendations, and errors

## 4. Failure Isolation

- [x] 4.1 Record analysis-stage errors without aborting the pipeline
- [x] 4.2 Record target-stage errors without aborting the pipeline
- [x] 4.3 Preserve ingestion source errors in the returned ingestion result

## 5. Tests And Verification

- [x] 5.1 Add offline end-to-end test from stub signal to stored thesis and target
- [x] 5.2 Add offline test for analysis failure isolation
- [x] 5.3 Add offline test for target generation failure isolation
- [x] 5.4 Add offline test for empty recommendation propagation
- [x] 5.5 Run `python3 -m pytest -q`
- [x] 5.6 Run `openspec validate add-pipeline-orchestration --strict`
