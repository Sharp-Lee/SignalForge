## MODIFIED Requirements

### Requirement: Three-step Thesis Orchestration
The analysis orchestration layer MUST run investment reasoning before thesis creation. If the audit is accepted, thesis creation MUST then run in this order: free generation by an author reasoner, completeness critique, then adversarial falsification by a reviewer reasoner. The completeness critique MUST record an audit object and MUST NOT rewrite the free-form thesis body. The adversarial reviewer MUST be independent from the author by instance id and persona.

#### Scenario: Accepted reasoning produces a confirmed thesis candidate
- **WHEN** investment reasoning returns an accepted audit and author/reviewer reasoners return valid free-generation, critique, and adversarial outputs
- **THEN** the orchestrator assembles a confirmed thesis with `body`, `investment_reasoning`, `completeness_critique`, `adversarial_falsification`, `track_record`, confidence, and source signal ids

#### Scenario: Weak reasoning stops before free generation
- **WHEN** investment reasoning returns a weak audit
- **THEN** the orchestrator does not call free generation, completeness critique, adversarial falsification, or thesis persistence

#### Scenario: Rejected reasoning stops before free generation
- **WHEN** investment reasoning returns a rejected audit
- **THEN** the orchestrator does not call free generation, completeness critique, adversarial falsification, or thesis persistence

#### Scenario: Completeness critique preserves body
- **WHEN** the critique step runs after free generation
- **THEN** the recorded `completeness_critique.body_unchanged` is true and the original `body` is preserved

#### Scenario: Self-review is rejected before confirmation
- **WHEN** the reviewer has the same instance id or persona as the author
- **THEN** the orchestrator MUST NOT confirm or persist the thesis
