## 1. Regression Tests

- [x] 1.1 Add offline test proving same persistent store second run has zero new theses and unchanged counts
- [x] 1.2 Add offline test proving a distinct second-run signal accumulates a new thesis and track record
- [x] 1.3 Add offline test proving a near-duplicate second-run signal is rejected across runs
- [x] 1.4 Add offline test proving show-store prints thesis/target counts and fields

## 2. Implementation

- [x] 2.1 Add `--store PATH` argument and persistent `ContractStore` selection for pipeline mode
- [x] 2.2 Create parent directories for persistent store paths
- [x] 2.3 Print cumulative thesis, target, and track_record counts after pipeline runs
- [x] 2.4 Add `--show-store PATH` mode and store summary printer
- [x] 2.5 Preserve tempfile behavior when `--store` is omitted

## 3. Verification

- [x] 3.1 Run targeted persistent-store tests
- [x] 3.2 Run full pytest suite
- [x] 3.3 Run `openspec validate add-persistent-store --strict`
- [x] 3.4 Run live same-store pipeline twice and show-store summary
