# signal-clustering Specification

## Purpose
TBD - created by archiving change add-signal-clustering. Update Purpose after archive.
## Requirements
### Requirement: Deterministic Signal Clusterer

The system MUST provide an injectable signal clustering module that groups accepted signals before analysis. The default clusterer MUST be deterministic and MUST run offline without LLM, embedding, network, or secret-dependent calls. The clusterer MUST return stable cluster ordering based on the input signal order.

#### Scenario: Clusterer runs without external providers
- **WHEN** tests invoke the default signal clusterer with fixture signals
- **THEN** it groups signals without calling an LLM, embedding service, network endpoint, or key-backed provider

#### Scenario: Clusterer can be injected
- **WHEN** pipeline tests supply a custom clusterer
- **THEN** the pipeline uses that clusterer rather than constructing provider-specific clustering logic internally

### Requirement: DF-Adaptive Salient Overlap

The default clusterer MUST compute relatedness using language-aware salient term overlap with batch-local document-frequency filtering. It MUST apply clustering-only normalization: HTML entity unescape, strip HTML/XML tags, and collapse whitespace. This normalization MUST NOT mutate stored signal body or raw payload.

The clusterer MUST compute `df_cutoff = ceil(batch_size * 0.5)` and MUST drop candidate terms whose document frequency in the current batch is greater than or equal to that cutoff. The implementation MUST NOT use a hand-maintained stopword list for feed-specific or run-specific common terms. In batches of 1 or 2 signals, this DF rule MAY conservatively remove shared terms and produce singleton clusters.

The default language routing MUST use CJK ratio over non-whitespace characters, with at least CJK Unified Ideographs `U+4E00`-`U+9FFF` counted as CJK. CJK-heavy pairs MUST use Chinese significant terms from alphanumeric model tokens and CJK 3-5 character grams. Non-CJK-heavy pairs MUST use English salient terms from token shape, including uppercase/acronym tokens, model/product tokens, and title/proper-shaped tokens. Mixed-language pairs MUST require explicit shared alphanumeric/model-token overlap.

#### Scenario: Batch common terms are filtered by DF
- **WHEN** a batch contains common source or run terms such as a site name or event name in at least half of the signals
- **THEN** the default clusterer removes those terms by document frequency rather than by a hardcoded stopword table

#### Scenario: Small batches degrade safely
- **WHEN** the current batch has only one or two signals
- **THEN** the default clusterer may return singleton clusters rather than forcing a low-evidence merge

#### Scenario: Stored signal text is not mutated
- **WHEN** clustering normalizes HTML-bearing signal text for feature extraction
- **THEN** the signal records passed to analysis retain their original body and raw payload

### Requirement: Conservative Cluster Formation

The default clusterer MUST form undirected relatedness edges between signal pairs and return connected components as analysis clusters. English pairs MUST require at least 4 shared DF-filtered salient terms. Chinese pairs MUST require at least 8 shared DF-filtered significant terms. Isolated signals MUST become singleton clusters.

The clusterer MUST prefer false negatives over false positives: it is acceptable for broad or low-evidence relationships to become separate singleton theses, but unrelated signals MUST NOT be merged merely because they share common source, event, year, or domain terms.

#### Scenario: English related signals cluster
- **WHEN** two English signals share enough concrete DF-filtered anchors such as product, vendor, model, or acronym terms
- **THEN** the default clusterer puts them in the same cluster

#### Scenario: English unrelated signals stay separate
- **WHEN** English signals only share batch-common or broad terms filtered by DF
- **THEN** the default clusterer keeps them in separate clusters

#### Scenario: Chinese related signals cluster
- **WHEN** two Chinese signals share enough DF-filtered alphanumeric model tokens or CJK 3-5 character terms
- **THEN** the default clusterer puts them in the same cluster

#### Scenario: Chinese unrelated signals stay separate
- **WHEN** Chinese signals have only weak or broad overlap below the Chinese threshold
- **THEN** the default clusterer keeps them in separate clusters

#### Scenario: Isolated signal becomes singleton
- **WHEN** a signal has no relatedness edge to any other signal in the current batch
- **THEN** the default clusterer returns it as a one-signal cluster

