## REMOVED Requirements

### Requirement: Runtime Behavior Remains Unchanged
**Reason**: Replaced by runtime application of the reasoning audit in analysis orchestration.
**Migration**: Use the new Runtime Analysis Gate requirement below.

## ADDED Requirements

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
