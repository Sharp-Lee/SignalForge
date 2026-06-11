## Context

`target_generation._assemble_target()` currently uses:

```python
"id": candidate.get("id") or _derive_target_id(symbol, thesis["id"])
```

That makes model-authored candidate ids authoritative. Real LLM output reused ids like `candidate-1` and `candidate-001` across different theses, which collided with the target table primary key. Pipeline-level isolation prevented a full run failure, but the affected thesis lost its target list.

The module already has the correct deterministic helper:

```python
_derive_target_id(symbol, thesis_id)
```

## Goals / Non-Goals

**Goals:**
- Make target ids deterministic and system-owned.
- Allow the same symbol to appear under different theses without collision.
- Skip duplicate symbols within a single thesis before persistence.
- Preserve existing contract enforcement and storage errors.

**Non-Goals:**
- No changes to LLM target prompts, schemas, or enforcement.
- No changes to `ContractStore`, target schema, or target validation.
- No broad `store.add_target()` try/except.
- No changes to market data, analysis, source ingestion, dedup, or clustering.

## Decisions

### D1 System-Derived Target Id

`_assemble_target()` will always set:

```python
"id": _derive_target_id(symbol, thesis["id"])
```

Model-provided `candidate["id"]` is ignored. This makes target identity match the domain object: a symbol considered under a specific thesis.

### D2 Per-Thesis Symbol Deduplication

`propose_targets()` will track symbols already accepted for the current thesis. If a later candidate has the same symbol, it is skipped before price lookup and target assembly with a rejected reason:

```text
<symbol>: duplicate symbol in thesis
```

The dedup set is local to one `propose_targets()` call. The same symbol under a different thesis remains legal because the derived target id includes `thesis_id`.

### D3 No Storage Error Masking

Do not wrap `store.add_target()` in a broad catch. If contract validation or storage fails for another reason, it should still surface to pipeline orchestration as a target-generation error. This change removes the known id-collision source rather than hiding persistence failures.

## Risks / Trade-offs

- [Risk] Downstream code might expect model candidate ids. -> Mitigation: candidate ids were never part of the target contract; target ids now become stable and derivable.
- [Risk] Duplicate symbol candidates may contain complementary rationale. -> Mitigation: MVP skips duplicates conservatively; a future ranking/merge change can combine rationale if needed.
