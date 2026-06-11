## 1. OpenSpec Artifacts

- [x] 1.1 Add `signal-contract` delta spec for language-aware near-duplicate dedup.

## 2. Core Implementation

- [x] 2.1 Update `news_contracts/validation.py` with dedup-only normalization, CJK ratio detection, language-aware tokenization, and default threshold `0.14`.
- [x] 2.2 Preserve `validate_signal()` / `_find_near_duplicate()` behavior and leave `dedup_hash()` unchanged.
- [x] 2.3 Document the design choice that false positives are worse than false negatives for signal dedup.

## 3. Regression Tests

- [x] 3.1 Add offline ServeTheHome English different-article fixtures and assert all six are accepted.
- [x] 3.2 Add English true near-duplicate regression coverage.
- [x] 3.3 Add Chinese different-article and Chinese true near-duplicate regression coverage.
- [x] 3.4 Add explicit known-miss test for heavy English paraphrase below threshold.
- [x] 3.5 Update existing dedup tests to the new metric and keep exact hash behavior covered.

## 4. Verification

- [x] 4.1 Run full `pytest tests/ -q`.
- [x] 4.2 Run `openspec validate fix-signal-dedup --strict`.
- [x] 4.3 Run the ServeTheHome live pipeline gate and confirm 6 accepted / 0 near-duplicate rejects.
