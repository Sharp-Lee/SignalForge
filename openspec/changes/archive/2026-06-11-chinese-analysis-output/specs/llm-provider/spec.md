## MODIFIED Requirements

### Requirement: Role Prompts And Thinking Policy

The provider MUST use role-specific system prompts and user prompts. Free generation, adversarial falsification, and target proposal MUST request adaptive thinking. Completeness critique MUST not request thinking. Reviewer prompts MUST use a hostile skeptic persona and must not produce `review_session`. Target proposal prompts MUST define `logic_score.score` as a 0-100 integer scale, include score anchors, and explicitly forbid 1-10 scoring. All role prompts MUST instruct the model to write human-readable prose, descriptions, rationales, notes, counterarguments, hedge variables, catalysts, and exit triggers in Simplified Chinese. Prompts MUST also instruct the model to keep existing enum field values as exact English tokens and never translate `direction`, `confidence`, or `buy_point.status`.

#### Scenario: Thinking policy is role-specific
- **WHEN** each role is invoked through injected transport
- **THEN** free generation, adversarial falsification, and target proposal pass adaptive thinking, while completeness critique passes no thinking

#### Scenario: Reviewer identity cannot be forged by model output
- **WHEN** adversarial falsification is returned
- **THEN** review session metadata is still created by orchestration, not by Claude

#### Scenario: Target score scale is explicit
- **WHEN** the target proposal role is invoked
- **THEN** the prompt instructs the model to emit `logic_score.score` as a 0-100 integer and not as a 1-10 score

#### Scenario: Human-readable output language is Chinese
- **WHEN** reasoner or target proposal prompts are built
- **THEN** system and user prompts instruct the model to write human-readable prose fields in Simplified Chinese

#### Scenario: Enum tokens remain English
- **WHEN** reasoner or target proposal prompts are built
- **THEN** system and user prompts instruct the model to keep `direction`, `confidence`, and `buy_point.status` values as exact English enum tokens
