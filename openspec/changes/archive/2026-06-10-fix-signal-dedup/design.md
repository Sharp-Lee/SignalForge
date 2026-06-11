## Context

The live ServeTheHome pipeline run fetched 6 RSS items but accepted only 1 signal. The other 5 were rejected as `near_duplicate`. Current dedup compares `signal["body"]` with existing bodies using whitespace-stripped character bigram Jaccard and default threshold `0.25`.

This was designed around Chinese text, where character n-grams are a reasonable proxy for words. It fails on English RSS because common letters, HTML markup, links, and site boilerplate make unrelated same-site articles look similar. Exact duplicate hashing via `dedup_hash(title + body)` is separate and must remain unchanged.

## Goals / Non-Goals

**Goals:**
- Replace the near-duplicate metric with one that works for CJK and whitespace-delimited languages.
- Recalibrate the default threshold using real English RSS samples and offline Chinese samples.
- Preserve exact duplicate hash behavior.
- Add regression tests covering English different, English true duplicate, Chinese different, and Chinese true near duplicate cases.
- Prove the fix with the same ServeTheHome live pipeline: 6 accepted, 0 `near_duplicate`.

**Non-Goals:**
- No pipeline orchestration changes.
- No source ingestion or RSS adapter changes.
- No clustering, summarization, embedding, or LLM-based dedup.
- No changes to `dedup_hash()`.
- No archive in this gate.

## Evidence Setup

Samples used for the gate:

- **English different:** the 6 current ServeTheHome RSS summaries from `https://www.servethehome.com/feed/`:
  - Minisforum S5 All-Flash NAS Shown Based on Intel's Wildcat Lake Platform
  - ServeTheHome Turns 17 The Places You Will Go
  - NXP Computex Keynote 2026 Coverage
  - A 40-Node 1U Cluster Gigabyte R1C7-K0A-AS1
  - Scoping Out RTX Spark SFF Mini-PCs at Computex 2026
  - Microsoft to Join the AI Dev Mini-PC Market With Upcoming Surface RTX Spark Dev Box
- **English true duplicate:** 3 paraphrased same-story pairs based on the Minisforum S5, Surface RTX Spark Dev Box, and Gigabyte 40-node cluster summaries.
- **Chinese different:** 6 same-domain but different investment/news snippets covering AI server optical modules, AI server power modules, HBM, liquid cooling, high-speed PCB, and ODM capacity.
- **Chinese true duplicate:** 2 near-duplicate pairs about HBM demand and AI server power-module lead times.

Important finding: using the raw RSS body with HTML still makes English word 2-shingle fail (`different max = 0.200`, `true duplicate min = 0.167`). Therefore the metric must include **dedup-only text normalization** before tokenization:

- HTML entity unescape.
- Strip HTML/XML tags.
- Collapse whitespace.

This normalization is only for similarity scoring inside `news_contracts/validation.py`; it does not mutate stored signal bodies or raw payloads.

## Candidate Metrics

All values below use normalized text unless noted. Values are Jaccard similarities.

| Candidate metric | English different max | English duplicate min | Chinese different max | Chinese duplicate min | Verdict |
|---|---:|---:|---:|---:|---|
| Current char 2-gram | 0.406 | 0.684 | 0.082 | 0.226 | Reject: no single threshold separates English different from Chinese duplicate; current 0.25 false-rejects English and can miss a Chinese near-duplicate. |
| Char 4-gram, language blind | 0.156 | 0.586 | 0.033 | 0.089 | Reject: no single threshold separates English different max 0.156 from Chinese duplicate min 0.089. |
| Char 5-gram, language blind | 0.128 | 0.550 | 0.017 | 0.073 | Reject: no single threshold separates English different max 0.128 from Chinese duplicate min 0.073. |
| Pure word / word shingle | 0.091 to 0.222 | 0.191 to 0.419 | up to 0.500 | down to 0.000 | Reject: Chinese degenerates without segmentation and can invert different vs duplicate. |
| Language-aware: CJK char 2-gram, English word 2-shingle | 0.091 | 0.191 | 0.082 | 0.226 | Recommend: one threshold cleanly separates all four classes. |

## Recommendation

Use a language-aware tokenization metric:

1. Normalize text for dedup scoring only.
2. Estimate CJK ratio over non-whitespace characters.
3. If CJK ratio is high enough, use character bigrams.
4. Otherwise, use word 2-shingles from lowercased alphanumeric tokens.
5. Compute Jaccard over the selected token sets.

Recommended CJK cutoff: `0.20`. This treats Chinese-heavy text as CJK while keeping English/HTML/RSS summaries on the word-shingle path.

Recommended default threshold: `0.14`.

Threshold margins with the evidence set:

| Class | Boundary | Similarity | Margin to 0.14 |
|---|---:|---:|---:|
| English different | max allowed below threshold | 0.091 | +0.049 |
| English true duplicate | min required above threshold | 0.191 | +0.051 |
| Chinese different | max allowed below threshold | 0.082 | +0.058 |
| Chinese true duplicate | min required above threshold | 0.226 | +0.086 |

This satisfies `max(different) < threshold < min(true duplicate)` across English and Chinese:

`0.091 < 0.14 < 0.191`.

## Approved Decisions

**D1 Metric:** use language-aware CJK char bigram / English word 2-shingle after dedup-only HTML normalization.

**D2 Threshold:** change `DEFAULT_DEDUP_THRESHOLD` from `0.25` to `0.14`.

**D3 Implementation scope:** keep the existing `validate_signal(..., dedup_threshold=...)` API and `_find_near_duplicate()` behavior, but replace `_jaccard()` tokenization internals. `dedup_hash()` remains unchanged.

## Risks / Trade-offs

- [Risk] Word 2-shingles may miss heavy paraphrases across sources. -> This change is calibrated for near-duplicate RSS/news snippets, not semantic duplicate detection; embeddings can be a later change if needed.
- [Risk] A single global threshold remains imperfect. -> The recommended metric is designed so one threshold works on the current bilingual evidence set; future larger fixtures can add per-language thresholds if needed.
- [Risk] HTML stripping inside validation duplicates some adapter concerns. -> This is dedup-only normalization and does not alter stored records, keeping ingestion/raw retention unchanged.

## Migration Plan

1. Update `news_contracts/validation.py`:
   - add dedup text normalization
   - implement language-aware tokenization
   - change default threshold to `0.14`
   - leave `dedup_hash()` untouched
2. Add offline regression fixtures/tests for all four required classes.
3. Run full `pytest`.
4. Create the `signal-contract` delta spec and tasks if reviewer wants the OpenSpec artifacts completed before implementation.
5. Run `openspec validate fix-signal-dedup --strict`.
6. Re-run ServeTheHome live pipeline and require 6 accepted / 0 near-duplicate rejects.

## Open Questions

None.
