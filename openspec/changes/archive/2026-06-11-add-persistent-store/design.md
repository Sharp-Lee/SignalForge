## Context

The live pipeline currently uses:

```python
with tempfile.TemporaryDirectory() as d:
    store = ContractStore(Path(d) / "pipeline.db")
```

This is useful for smoke runs, but it discards durable system memory. `ContractStore` already has the required persistence behavior:

- `create table if not exists` makes reopening an existing db safe.
- `source_cursors` stores adapter cursors for incremental fetching.
- `signals` persists payloads and dedup history.
- `theses`, `targets`, and `track_record` persist system outputs.

## Goals / Non-Goals

**Goals:**
- Add an explicit persistent store path for live pipeline runs.
- Preserve tempfile behavior when no store path is supplied.
- Add a read-only summary view for accumulated theses and targets.
- Prove same-feed repeated runs do not duplicate signals, theses, targets, or track records.

**Non-Goals:**
- No changes to `ContractStore` schema or storage semantics.
- No changes to pipeline orchestration, ingestion, analysis, target generation, or dedup logic.
- No migration/versioning system for store files.
- No interactive UI.

## Decisions

### D1 Optional Store Path

Add:

```text
scripts/run_live.py --pipeline --store PATH
```

When `--store` is supplied:

- expand `~`;
- create the parent directory;
- pass that path to `ContractStore`.

When omitted, keep the current temporary store behavior so smoke runs do not pollute persistent data.

### D2 Read-Only Store Summary

Add:

```text
scripts/run_live.py --show-store PATH
```

This mode opens the existing store and prints:

- thesis total and rows: id, direction, confidence, status, body preview, verification window;
- target total and rows: symbol, name, logic score, buy point status, priced-in risk, price change since signal.

It does not call providers or mutate the store intentionally. `ContractStore` may create tables if pointed at an empty db, but normal usage is an existing store path.

### D3 Cumulative Counts

After a pipeline run, print current database totals for theses, targets, and track records. `new_signal_count` remains the current-run ingestion accepted count. This makes the difference between "this run found no new articles" and "the store already contains accumulated data" visible.

## Risks / Trade-offs

- [Risk] Users can point `--show-store` at a nonexistent path and create an empty sqlite file through `ContractStore`. -> Mitigation: check file existence before opening for show-store and fail clearly if missing.
- [Risk] Reusing a persistent store means source cursor state suppresses repeat ingestion. -> Mitigation: this is the intended behavior and is verified with a same-feed double run.
- [Risk] Store files contain personal investment notes. -> Mitigation: no secrets are printed; store files are local and not committed by this change.
