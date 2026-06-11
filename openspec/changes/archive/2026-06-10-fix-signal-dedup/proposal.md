## Why

The first live full-pipeline RSS run showed that the current near-duplicate detector drops distinct English RSS items as `near_duplicate`. ServeTheHome fetched 6 different articles but only 1 entered analysis because character bigram Jaccard at threshold 0.25 treats same-language/same-site boilerplate as duplicate content.

## What Changes

- Recalibrate signal near-duplicate detection with evidence from English RSS items, English true duplicates, Chinese different items, and Chinese true near duplicates.
- Replace the current language-blind character bigram similarity with a language-aware similarity metric after minimal dedup-only text normalization.
- Keep `dedup_hash()` exact duplicate hashing unchanged.
- Preserve configurable threshold behavior, but update the default threshold only after reviewer approval of the evidence table.
- Add offline regression fixtures covering English different articles, English true duplicates, Chinese different articles, and Chinese true near duplicates.
- Re-run the live ServeTheHome pipeline and require 6 accepted signals and 0 `near_duplicate` rejects.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `signal-contract`: near-duplicate deduplication behavior and default similarity threshold are changing.

## Impact

- Affected implementation:
  - `news_contracts/validation.py`
  - `tests/`
- Explicitly not affected:
  - `dedup_hash()` exact duplicate hashing
  - `pipeline_orchestration/`
  - `source_ingestion/`
  - `llm_provider/`
  - `analysis_orchestration/`
  - `target_generation/`
- This change is not archived until reviewer approval, tests, OpenSpec strict validation, and live pipeline verification complete.
