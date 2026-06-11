## Context

The first live DeepSeek target-generation run reached the target proposal path and exposed two grounding gaps. DeepSeek emitted `logic_score.score` on a 1-10 scale even though provider enforcement and target generation gates treat scores as 0-100. It also paired an allowed symbol with a hallucinated company name because the current provider only checks `symbol in universe` and trusts model-authored `name`.

The target layer's stable boundary remains unchanged: the LLM proposes investment judgments, target generation assembles target records, and `ContractStore.add_target()` remains the canonical persistence/contract gate. This change hardens the model-facing seam by moving reference data authority out of the model.

## Goals / Non-Goals

**Goals:**
- Pin target proposal scoring to a 0-100 integer scale in prompts and enforce the existing 0-100 range.
- Treat the target universe as authoritative reference data: `dict[symbol, company_name]`.
- Remove model-authored company names from target proposal schema.
- Stamp target candidate names from the authoritative universe before assembly.
- Keep out-of-universe symbols fail-closed.
- Update tests and live harness fixtures to the authoritative universe shape.
- Prove the fix with a real DeepSeek `--targets` run that produces at least one persisted target.

**Non-Goals:**
- No transport changes.
- No analysis orchestration changes.
- No real market-data integration; live harness prices remain stubs.
- No archive in this change.
- No broad target ranking, dynamic thresholds, calibration, or user-decision workflow.

## Decisions

**D1 Authoritative universe becomes `dict[str, str]`.**  
The target universe must carry both the allowed symbol and the authoritative company name. A set only answers "is this symbol allowed"; it cannot prevent name hallucination. The model-facing prompt may include the mapping for context, but authority remains in system code.

**D2 Model no longer outputs target `name`.**  
`TARGET_PROPOSAL_SCHEMA` removes `name` from required fields and properties. `enforce_target_candidates()` stamps `candidate["name"] = symbol_universe[symbol]` after checking that `symbol` exists. `_assemble_target()` can keep reading `candidate["name"]`, but the value is now system-owned.

**D3 Score scale is pinned in both system and user prompts.**  
The target system prompt and rendered user prompt must explicitly state `logic_score.score` is a 0-100 integer. Anchors:
- 80-100 = strong direct beneficiary
- 60-79 = moderate or conditional beneficiary
- 40-59 = weak / second-order / edge exposure
- below 40 = mostly unrelated

The prompt must explicitly forbid 1-10 scoring. Provider enforcement continues to reject scores outside 0-100.

**D4 Candidate malformed handling uses approved Option B.**  
Current behavior raises `LlmProviderError` for any candidate missing catalysts/exit triggers, which rejects the whole batch before `propose_targets()` can return an empty recommendation with reasons. Two options:

- **Option A: batch raise for every malformed candidate.** This is simple and maximally strict, but one otherwise irrelevant bad candidate can hide valid candidates and makes live target generation brittle.
- **Option B: split hard hallucinations from per-candidate quality failures.** Keep batch raise for hallucination/grounding failures such as missing universe, non-list candidates, out-of-universe symbols, invalid score type/range, or invalid buy point enum. Convert per-candidate completeness failures such as missing catalysts, missing exit triggers, ineligible, or below-threshold logic score into rejected reasons handled by target generation.

Reviewer decision: **Option B is approved with an empty-vs-damaged split**.

Batch raise remains in provider enforcement for structure, hallucination, and untrusted values:
- no universe
- `candidates` is not an array
- symbol outside universe
- score type/range invalid
- buy point enum invalid
- empty `logic_score.rationale` or `buy_point.rationale`
- catalyst/exit-trigger elements exist but are structurally damaged, such as missing non-empty `description`

Per-candidate rejection remains in `propose_targets()` for quality/completeness:
- `eligible=false`
- `logic_score` below threshold
- price lookup missing
- `catalysts` empty or missing
- `exit_triggers` empty or missing

This keeps hallucinations fail-closed while preventing one empty candidate from discarding the whole batch. It also avoids creating a new hole: non-empty but malformed catalyst/exit-trigger elements still raise before they can reach `ContractStore.add_target()`.

## Risks / Trade-offs

- [Risk] Prompt scale anchors may still be ignored by some models. -> Keep provider range enforcement and require live DeepSeek verification.
- [Risk] Universe dict can become stale. -> Keep it injected as fixture/reference data in this change; production source maintenance is separate.
- [Risk] Removing `name` from model output can reduce model context. -> Include symbol-name mapping in the prompt input, but stamp the value from code.
- [Risk] Option B can mask repeated low-quality candidates. -> Preserve `rejected_reasons` so review can see failure patterns.

## Migration Plan

1. Update `llm-provider` target prompt/schema/enforcement.
2. Update `target_generation` protocols and callers from set universe to dict universe.
3. Update tests and live harness fixtures.
4. Run full offline tests and OpenSpec strict validation.
5. Run `python scripts/run_live.py --author deepseek --targets` with redaction and verify persisted target output.

## Open Questions

None.
