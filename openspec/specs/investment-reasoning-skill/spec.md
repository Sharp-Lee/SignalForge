# investment-reasoning-skill Specification

## Purpose
Defines the structured reasoning audit used to apply the investment-logic taxonomy to concrete signals before chokepoint-map lookup or target mapping.

## Requirements
### Requirement: Investment Reasoning Audit Shape
The system SHALL define an `InvestmentReasoningAudit` structure for applying the investment-logic taxonomy to a concrete signal or signal cluster. The audit MUST include source signal ids, exactly one primary logic type, optional secondary logic types, evidence status, premise, upward validation, transmission chain, downstream decomposition, chokepoint candidates, target-search decision, missing evidence, disconfirming evidence, and public caveat.

#### Scenario: Audit captures a full reasoning chain
- **WHEN** a signal is evaluated for investment logic
- **THEN** the audit records the primary logic type, validation chain, downstream decomposition, missing evidence, disconfirming evidence, and public caveat

### Requirement: Canonical Logic Type Use
The audit MUST use canonical logic type values from `investment-logic-taxonomy`. It MUST contain exactly one `primary_logic_type` and MAY contain zero or more `secondary_logic_types`.

#### Scenario: Primary logic is required
- **WHEN** an audit is created
- **THEN** it contains exactly one primary logic type from the canonical taxonomy

#### Scenario: Unknown logic is rejected
- **WHEN** an audit contains a logic type outside the canonical taxonomy
- **THEN** future schema or enforcement MUST reject the audit rather than silently accepting the invented label

### Requirement: Evidence Status Gates Target Search
The audit MUST classify evidence as `accepted`, `weak`, or `rejected`. Target search MAY be allowed only when evidence status is `accepted`. If evidence status is `weak` or `rejected`, the audit MUST set the target-search decision to a non-allowed state such as `not_ready` or `blocked`.

#### Scenario: Accepted logic can proceed
- **WHEN** an audit has `evidence_status: accepted`
- **THEN** the target-search decision may be `allowed` if the transmission chain and downstream decomposition are present

#### Scenario: Weak logic does not proceed to targets
- **WHEN** an audit has `evidence_status: weak`
- **THEN** the target-search decision is not allowed and the audit records missing evidence

#### Scenario: Rejected logic blocks target search
- **WHEN** an audit has `evidence_status: rejected`
- **THEN** the target-search decision is blocked and no target mapping is implied

### Requirement: Audit Preserves Free-Form Thesis Body
The audit SHALL be advisory metadata or a reasoning-audit artifact. It MUST NOT replace the free-form thesis body, force the thesis body into a fixed table, or weaken existing thesis-contract requirements for completeness critique, adversarial falsification, traceability, and track record.

#### Scenario: Thesis prose remains free
- **WHEN** the audit is used by a future analysis implementation
- **THEN** the thesis body may remain free-form prose
- **AND** the audit remains separate from the body structure

### Requirement: Chokepoint Candidates Are Not Recommendations
The audit MAY include chokepoint candidates as memory lookup hints. Chokepoint candidates MUST NOT be treated as proof, target recommendations, or a shortcut around target-contract validation.

#### Scenario: Chokepoint candidate only narrows investigation
- **WHEN** an audit lists a chokepoint candidate
- **THEN** the candidate is treated as a node to investigate
- **AND** it does not itself create a target or recommendation

### Requirement: Public Caveat For Digest Use
The audit MUST include a public caveat that states the logic's dependency and uncertainty in research-note language. The caveat MUST avoid recommendation language such as "buy", "recommend", "target price", or "sure opportunity".

#### Scenario: Public caveat is digest-safe
- **WHEN** an audit is later rendered into a public digest
- **THEN** the caveat describes the logic as a research observation and states what evidence could weaken it

### Requirement: Local Schema And Validator
The system SHALL provide a local `investment_reasoning` module exposing canonical logic values, an `InvestmentReasoningAudit` JSON Schema, and a fail-closed validation function. The validator MUST run offline and MUST NOT call an LLM, network, market data provider, storage layer, or target generator.

#### Scenario: Validator accepts a valid audit offline
- **WHEN** a valid audit is passed to the validator with known source signal ids
- **THEN** the validator returns the audit without calling external services

#### Scenario: Validator rejects invalid audit gates
- **WHEN** a weak or rejected audit allows target search
- **THEN** the validator rejects it before any downstream target mapping can be implied

### Requirement: Runtime Analysis Gate
The system SHALL apply `InvestmentReasoningAudit` as a runtime gate before free-form thesis generation in analysis orchestration. Accepted audits MAY proceed to thesis generation. Weak or rejected audits MUST stop before thesis generation and MUST NOT imply target mapping.

#### Scenario: Accepted audit proceeds
- **WHEN** a selected signal cluster produces an accepted investment reasoning audit
- **THEN** analysis may continue into free-form thesis generation, completeness critique, adversarial review, and contracted thesis persistence

#### Scenario: Weak audit stops analysis
- **WHEN** a selected signal cluster produces a weak investment reasoning audit
- **THEN** analysis stops before thesis generation
- **AND** no target mapping is implied

#### Scenario: Rejected audit stops analysis
- **WHEN** a selected signal cluster produces a rejected investment reasoning audit
- **THEN** analysis stops before thesis generation
- **AND** no target mapping is implied
