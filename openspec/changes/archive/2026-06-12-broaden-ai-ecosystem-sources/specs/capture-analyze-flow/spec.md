## ADDED Requirements

### Requirement: AI Ecosystem Signal Priority Hints
The analyze path's cheap cluster scoring SHALL recognize AI ecosystem infrastructure terms beyond semiconductor/server hardware, including power, energy, data-center, cooling, grid, utility, storage, and AI software/adoption terms. These hints MUST remain deterministic input-side prioritization and MUST NOT replace LLM thesis reasoning.

#### Scenario: Energy infrastructure signal receives priority hint
- **WHEN** a pending signal mentions data-center power, grid, utility, cooling, storage, solar, or megawatt terms
- **THEN** cheap cluster scoring treats it as relevant AI ecosystem infrastructure

#### Scenario: Software adoption signal receives priority hint
- **WHEN** a pending signal mentions AI agents, inference, enterprise AI, or AI software adoption
- **THEN** cheap cluster scoring treats it as relevant AI ecosystem context
