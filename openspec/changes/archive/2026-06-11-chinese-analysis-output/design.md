## Context

The system reads mostly English global technology signals, then produces thesis and target outputs used by a Chinese daily digest. Current prompts do not specify output language, so live DeepSeek follows the English source text and emits English prose.

The contracts and provider enforcement intentionally keep enum fields as English tokens. If prompts ask for "all Chinese" without an exception, the model may translate `direction`, `confidence`, or `buy_point.status`, causing provider or contract rejection.

## Goals / Non-Goals

**Goals:**

- Make human-readable thesis and target prose Simplified Chinese.
- Keep machine enum values as the existing English tokens.
- Add prompt-level tests for system and user prompt guardrails.
- Prove the behavior with a live DeepSeek run and digest generation.

**Non-Goals:**

- No schema changes.
- No validation/enforcement changes.
- No transport changes.
- No analysis or target orchestration changes.
- No digest formatting change.
- No Chinese translation post-processor.

## Decisions

### D1 Prompt-Only Language Control

Implement language control only in `llm_provider/prompts.py`.

Rationale: language choice belongs at the LLM role boundary. The contracts already define accepted structure and enums; adding translation logic elsewhere would duplicate responsibility and could hide provider drift.

### D2 Repeat The Guardrail In System And User Prompts

Add the instruction to all four role system prompts:

```text
All human-readable prose/descriptions/rationales must be written in Simplified Chinese.
Enum field values must remain exact English tokens and must never be translated:
direction(bullish/bearish/neutral/mixed), confidence(low/medium/high),
buy_point.status(favorable/neutral/unfavorable).
```

Add equivalent rules to `render_reasoner_user()` and `render_target_user()` payloads.

Rationale: real providers sometimes follow the user prompt more strongly than the system prompt when output fields are close to the schema. Duplicating the constraint is cheap and keeps the change in the prompt layer.

### D3 Field Boundary

Human-readable fields should be Chinese:

- `body`
- `substantive_claims[].text`
- `transmission_path[].description`
- `falsifiable_expectation`
- `uncertainty_tags`
- completeness critique `notes`
- `strongest_counterargument`
- `hedge_variables`
- `logic_score.rationale`
- `buy_point.rationale`
- `catalysts[].description`
- `exit_triggers[].description`

Machine fields must not be translated:

- `direction`
- `confidence`
- `buy_point.status`
- `source_signal_ids`
- `verification_window`
- `symbol`

`origin_market` and `target_market` are free text and may be Chinese.

## Risks / Trade-offs

- Model may still translate enum values despite prompts -> live validation will catch this; strengthen prompt wording and rerun if needed.
- Chinese prose may be less grounded if the model summarizes English sources too loosely -> provenance enforcement still requires source ids, and live output must be reviewed.
- Prompt-only control cannot guarantee every token is Chinese -> acceptable for this change; the requirement is human-readable prose, not a deterministic translation pass.

## Migration Plan

1. Add prompt tests that fail on current prompts.
2. Update `llm_provider/prompts.py` only.
3. Run full offline tests.
4. Validate the OpenSpec change.
5. Run live DeepSeek pipeline and inspect Chinese prose plus English enum validity.
6. Generate a digest from real data and inspect one logic card.
