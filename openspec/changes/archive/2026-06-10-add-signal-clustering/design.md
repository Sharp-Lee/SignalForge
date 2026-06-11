## Context

`pipeline_orchestration.run_pipeline()` currently persists incoming signals, reads every signal added in the current run, and passes the entire list to one `analyze()` call. That was acceptable as an MVP boundary, but live RSS now preserves distinct items correctly. The next failure is over-aggregation: unrelated signals are forced into one thesis, which weakens traceability and makes the thesis body incoherent.

Signal clustering sits immediately before analysis. It must be deterministic, offline, and injectable. It must not call an LLM or embedding service in this change. The purpose is only to form coherent input groups; the analysis layer still owns thesis generation, completeness critique, and adversarial falsification.

## Goals / Non-Goals

**Goals:**
- Group newly persisted signals into coherent clusters before `analyze()`.
- Preserve isolated signals by emitting singleton clusters.
- Preserve cross-signal synthesis when signals are truly related.
- Keep pipeline stage resilience: one bad cluster does not abort the run.
- Keep clustering deterministic, offline, and unit-testable.
- Support English and Chinese without relying on English-only capitalization.

**Non-Goals:**
- No LLM clustering.
- No embedding similarity.
- No signal ranking, theme scheduling, or daily/event/weekly policy.
- No changes to `analysis_orchestration`, `target_generation`, `llm_provider`, `news_contracts`, or dedup.
- No attempt to solve semantic paraphrase clustering beyond explicit shared entities / salient terms.

## Decision Gate Summary

**Recommended R1:** deterministic language-aware salient-overlap clustering with batch-local DF filtering.

1. Extract candidate salient terms from each signal using language-aware shape rules.
2. Compute document frequency across the current signal batch.
3. Remove any candidate term whose document frequency is `>= ceil(batch_size * 0.5)`.
4. Build pairwise relatedness edges using the remaining shared terms.
5. Connected components over related edges become clusters.
6. Signals with no related edges become singleton clusters.

This intentionally favors false negatives over false positives. A missed relation still produces two theses that a human can compare; a false cluster contaminates the analysis input and can produce a confused thesis.

## Proposed Interface

Create a small module such as `signal_clustering/`:

```python
@dataclass
class SignalCluster:
    id: str
    signals: list[dict]
    reason: str

class SignalClusterer(Protocol):
    def cluster(self, signals: list[dict]) -> list[SignalCluster]: ...
```

`run_pipeline()` receives `clusterer=None`. When absent, it uses the default deterministic clusterer. Tests can inject a fake clusterer to force multiple groups without depending on feature details.

## Features And Algorithm

### Normalization

Use `title + "\n" + body` for clustering text. Apply clustering-only normalization:

- HTML entity unescape.
- Strip HTML/XML tags.
- Collapse whitespace.
- Do not mutate stored signal body or raw payload.

### Language Routing

Compute CJK ratio over non-whitespace characters using at least CJK Unified Ideographs `U+4E00`-`U+9FFF`.

- If both signals are CJK-heavy (`ratio >= 0.20`), compare Chinese significant terms.
- If both are non-CJK-heavy, compare English salient terms.
- If mixed, compare only shared alphanumeric/model tokens after the same DF filter and require a conservative explicit overlap.

### Batch-Local DF Filtering

No manual stopword or feed-specific term table is allowed. Common run terms must be removed by current-batch document frequency:

```text
df_cutoff = ceil(batch_size * 0.5)
drop term when document_frequency(term) >= df_cutoff
```

For the ServeTheHome 6-item fixture, this automatically removes `2026`, `computex`, `servethehome`, and `the`. These are examples of terms the DF rule discovers; they are not constants.

For small batches, this is intentionally conservative. With 1-2 signals, `df_cutoff` removes nearly all shared terms, so clustering naturally degrades to singleton clusters. That is acceptable for this MVP because it avoids reintroducing the mush bug.

### English Feature

Extract candidate terms by token shape, not by hand-maintained stop tables:

- uppercase/acronym tokens such as `RTX`, `NXP`, `SFF`;
- model/product tokens with digits or punctuation such as `R1C7-K0A-AS1`, `1U`, `10GbE`;
- title/proper-shaped tokens such as `Microsoft`, `Surface`, `NVIDIA`, `Spark`;
- hyphenated/model tokens may contribute both full token and component tokens;
- then apply batch-local DF filtering.

Pair is related when shared English terms after DF filtering are `>= 4`.

### Chinese Feature

Because Chinese has no capitalization signal and no NER dependency in this change, extract deterministic significant terms:

- alphanumeric model tokens such as `HBM3E`, `800G`, `PCB`, `ODM`;
- CJK 3-5 character grams from normalized text;
- then apply the same batch-local DF filtering.

No hardcoded Chinese stop list is allowed. Common Chinese run terms such as repeated years, broad theme words, or source boilerplate must be removed only when the current batch DF rule identifies them.

Pair is related when shared Chinese terms after DF filtering are `>= 8`.

### Grouping

After pairwise relatedness is computed:

1. Add an undirected edge for every related pair.
2. Return connected components in stable input order.
3. Return singleton components for isolated signals.

Connected components allow chains such as A related to B and B related to C to produce one cluster. This is desirable for accumulating a transmission path across several related signals, but it increases false-positive risk. The pair thresholds above are therefore deliberately conservative.

## Evidence Table

Samples:

- English: the 6 ServeTheHome RSS items from the live feed run:
  1. Minisforum S5 all-flash NAS
  2. ServeTheHome 17th anniversary
  3. NXP Computex keynote
  4. Gigabyte 40-node 1U cluster
  5. RTX Spark SFF mini-PCs from ASUS/Dell/Lenovo/MSI
  6. Microsoft Surface RTX Spark Dev Box
- English true related pair: 5 and 6.
- Chinese: 8 offline snippets:
  - 6 unrelated supply-chain items covering 800G optical modules, AI server power modules, HBM3E capacity, liquid cooling, PCB materials, and Mexico server assembly capacity.
  - 2 true related pairs: HBM3E capacity pair, AI server power-module lead-time pair.

### Candidate Comparison

| Candidate | English true related | English unrelated max | Chinese true related min | Chinese unrelated max | Verdict |
|---|---:|---:|---:|---:|---|
| Dedup word 2-shingle Jaccard | flat 0.06-0.09 on ServeTheHome | flat 0.06-0.09 | not evaluated for clustering | not evaluated for clustering | Reject: designed for near-duplicate detection, not topical relation. |
| Word unigram Jaccard | around 0.30 before aggressive stop filtering | around 0.20-0.22 before aggressive stop filtering | weak without segmentation | noisy | Reject: tail noise is high; Chinese degrades without segmentation. |
| Manual-stop salient overlap | English related can separate | fragile | Chinese depends on hand list | fragile | Reject: overfits the feed; the mush bug can return when common terms are not anticipated. |
| DF-adaptive language-aware salient overlap | English: 6 | English: 1 | Chinese: 11 | Chinese: 3 | Recommend: clean margins without manual stop tables. |

### DF-Adaptive Evidence

| Route | Batch size | DF cutoff | Terms removed by DF | Related threshold | Related min | Unrelated max | Margin |
|---|---:|---:|---|---:|---:|---:|---:|
| English ServeTheHome | 6 | `>= 3` | `2026`, `computex`, `servethehome`, `the` | `>= 4` | 6 | 1 | +2 to related, +3 over unrelated |
| Chinese fixture | 8 | `>= 4` | none in this fixture | `>= 8` | 11 | 3 | +3 to related, +5 over unrelated |

English unrelated residual overlaps after DF filtering were weak incidental terms such as `with` or broad `ai`, with max shared count `1`. The RTX Spark pair retained six concrete shared anchors: `mini`, `mini-pc`, `nvidia`, `rtx`, `soc`, `spark`.

Chinese related pairs retained dense concrete overlaps:

- AI server power-module lead time pair: 17 shared terms, including `odm`, `功率电源`, `电源模块`, `电源交期`.
- HBM3E capacity pair: 11 shared terms, including `hbm`, `hbm3e`, `供应商`, `先进封装`, `年产能`.

The Chinese unrelated max was 3, from broad but insufficient partial overlaps such as `交付周期`. That remains below the `>= 8` threshold.

The English evidence clusters only the RTX Spark pair and leaves NAS, anniversary, NXP, and Gigabyte as singleton clusters. The NXP keynote may be broadly "edge AI" related, but it does not share enough concrete product/entity anchors with RTX Spark to justify feeding it into the same thesis in this deterministic MVP.

## Pipeline Changes After Approval

If R1 is approved:

1. Add `signal_clustering` default clusterer and protocol.
2. Change `run_pipeline()` to:
   - ingest;
   - load newly persisted signals;
   - call `clusterer.cluster(signals)`;
   - run `analyze()` independently per cluster;
   - run `propose_targets()` independently per successful thesis;
   - record `PipelineError(stage="analysis", unit=<cluster-id>, ...)` per failed cluster.
3. Keep `PipelineResult.theses`, `targets`, `empty_recommendations`, and `errors` as lists.
4. Update `scripts/run_live.py --pipeline` only if it assumes a single thesis in printing.

## Risks / Trade-offs

- [Risk] Conservative thresholds miss some broad thematic relationships. -> Accept for MVP; singleton theses are recoverable and safer than confused merged theses.
- [Risk] Small batches of 1-2 related signals degrade to singleton clusters. -> Accept as a deliberate safety property; later changes can add richer evidence such as embeddings.
- [Risk] Connected components can chain a weak bridge into a larger cluster. -> Conservative pair thresholds and DF filtering reduce this; tests should include unrelated singleton cases.
- [Risk] Chinese CJK grams can over-link same-domain stories. -> Use 3-5 grams, batch-local DF filtering, and a high overlap threshold; avoid bigrams.
- [Risk] Entity extraction is heuristic. -> Keep the module injectable so a later embedding or LLM clusterer can replace it behind the same interface.
- [Risk] ServeTheHome live output may produce several LLM calls and cost more. -> This is expected for the live gate; production scheduling/ranking remains later work.

## Approved Decisions

- R1-fix approved: use DF-adaptive language-aware salient-overlap clustering with `df_cutoff = ceil(batch_size * 0.5)`, English threshold `>= 4`, Chinese threshold `>= 8`, connected-component grouping, and singleton fallback.

## Open Questions

None.
