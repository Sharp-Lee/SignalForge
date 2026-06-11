## Context

The target proposal schema allows:

```json
"kind": {"type": ["string", "null"]},
"value": {"type": ["string", "null"]}
```

This is correct at the model boundary because the model may know a catalyst description without knowing the right classification or compact value.

The target contract requires catalyst `description` but makes `kind` and `value` optional. If present, they must be strings. This is also correct: persisted contracts should not store `null` for optional string fields.

The drift is in `_assemble_target()`, which currently copies candidate catalyst dictionaries into the persisted target unchanged.

## Goals / Non-Goals

**Goals:**
- Preserve valid targets when proposal metadata contains `None` for optional catalyst or exit-trigger keys.
- Keep non-null catalyst and exit-trigger metadata intact.
- Let `target-contract` continue enforcing malformed persisted records.

**Non-Goals:**
- No changes to `target-contract` schema.
- No changes to `TARGET_PROPOSAL_SCHEMA`.
- No changes to `enforce_target_candidates()`.
- No changes to target ranking, state transitions, or market data.

## Decisions

### D1 Drop Null Optional Keys At Assembly

Add a small assembly helper:

```python
def _drop_null(record):
    return {key: value for key, value in record.items() if value is not None}
```

Use it for:

```python
"catalysts": [_drop_null(c) for c in candidate.get("catalysts") or []],
"exit_triggers": [_drop_null(t) for t in candidate.get("exit_triggers") or []],
```

This converts model `{"kind": None, "value": None, "description": "..."}` into persisted `{"description": "..."}`. The contract accepts the latter because `kind` and `value` are optional.

### D2 Keep Required Field Enforcement Elsewhere

Do not use this helper to silently repair missing or empty `description`. Existing enforcement and contract validation should still reject structurally bad records.

## Risks / Trade-offs

- [Risk] Dropping nulls can hide that the model was uncertain about metadata classification. -> Mitigation: only optional metadata keys are removed; the human-readable description remains intact.
- [Risk] Future optional fields may need different semantics. -> Mitigation: the helper only removes Python `None`, not empty strings, falsey values, or malformed types.
