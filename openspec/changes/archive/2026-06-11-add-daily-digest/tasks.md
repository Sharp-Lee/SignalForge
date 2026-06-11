## 1. Planning

- [x] 1.1 Validate `add-daily-digest` planning artifacts with OpenSpec strict mode

## 2. Digest Generator

- [x] 2.1 Add `scripts/generate_digest.py` CLI with `--store`, `--date`, and `--out`
- [x] 2.2 Read persistent SQLite store in read-only mode
- [x] 2.3 Select same-day theses via `track_record.created_at`
- [x] 2.4 Render current watchlist targets with Chinese labels and safe formatting
- [x] 2.5 Write Markdown and inline-style HTML outputs
- [x] 2.6 Generate "今日无新增" output for missing/empty/no-new-content stores

## 3. Tests And Documentation

- [x] 3.1 Add offline fixture-store test for Markdown/HTML content
- [x] 3.2 Add empty-store/no-new-content test
- [x] 3.3 Add read-only/counts-unchanged test
- [x] 3.4 Document digest generation in README

## 4. Verification

- [x] 4.1 Run `python -m pytest tests/ -q`
- [x] 4.2 Run `openspec validate add-daily-digest --strict`
- [x] 4.3 Generate a digest from the real local store and review Markdown output

## 5. Logic-Chain Revision

- [x] 5.1 Update tests for source-information-to-logic-to-target cards
- [x] 5.2 Group targets by supporting thesis instead of rendering one global watchlist
- [x] 5.3 Render source title, source name, published time, and URL per thesis
- [x] 5.4 Render world context, support logic, confirmed logic, counterargument, and selected targets per card
- [x] 5.5 Re-run full tests, OpenSpec strict validation, and real-store digest generation

## 6. Public Digest Compliance Wording

- [x] 6.1 Remove buy-point status from Markdown and HTML target rendering
- [x] 6.2 Rename target card section to observation-object wording
- [x] 6.3 Render catalysts as observation conditions and exit triggers as invalidation conditions
- [x] 6.4 Add fallback display for missing observation or invalidation conditions
- [x] 6.5 Update digest tests and OpenSpec wording
