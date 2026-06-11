## MODIFIED Requirements

### Requirement: Composition-only Pipeline

`run_pipeline` MUST compose the existing ingestion, analysis, and target-generation layer functions with an existing `ContractStore`. It MUST NOT reimplement contract validation, analysis assembly, target assembly, or persistence. Operation-layer harnesses MAY choose whether that `ContractStore` is temporary or persistent.

#### Scenario: Pipeline calls existing layer functions
- **WHEN** a pipeline run executes
- **THEN** it uses `run_once`, `analyze`, and `propose_targets` rather than writing layer records directly

#### Scenario: Pipeline writes through ContractStore-backed layers
- **WHEN** pipeline produces theses or targets
- **THEN** those records have passed through their existing `ContractStore` persistence paths

#### Scenario: Live harness injects persistent store
- **WHEN** the live harness is run with a store path
- **THEN** it injects a persistent `ContractStore` into `run_pipeline` without changing pipeline internals
