## 1. Regression Tests

- [x] 1.1 Add test proving catalyst `kind=None` and `value=None` are omitted and target validates
- [x] 1.2 Add test proving non-null catalyst metadata is preserved

## 2. Implementation

- [x] 2.1 Add target assembly helper that drops only `None` values from catalyst/exit-trigger dictionaries
- [x] 2.2 Use helper when assembling catalysts
- [x] 2.3 Use helper when assembling exit triggers

## 3. Verification

- [x] 3.1 Run targeted target-generation tests
- [x] 3.2 Run full pytest suite
- [x] 3.3 Run `openspec validate fix-catalyst-kind-drift --strict`
- [x] 3.4 Run live pipeline gate and confirm no catalyst null-kind contract error
