## Context

The live pipeline currently runs capture and analysis as one coupled operation:

```text
run_once(adapters)
-> compute newly persisted signals by before/after diff
-> cluster all new signals
-> analyze every cluster
-> propose targets
```

This works for small RSS runs, but it does not scale to日内多次采集. If a day accepts hundreds of deduplicated signals, the LLM path can run too long and create a noisy digest. More importantly, if the process crashes after capture but before analysis, those signals are no longer "new in this run" next time and can be missed by the analysis path.

The right-sized MVP is not a full attention system. The valuable change is:

```text
capture often, persist everything accepted
analyze later from pending accepted signals, with a small top-K cap
```

## Goals / Non-Goals

**Goals:**
- Make source capture independent from LLM analysis.
- Keep accepted signals pending until an analyze run marks them terminal (`analyzed`, `skipped_stale`, or `skipped_failed`).
- Let analyze runs read pending signals, cluster them with the existing clusterer, cheaply rank clusters, and analyze only top-K clusters.
- Leave unselected clusters pending for a later run.
- Retire stale pending signals after a configurable age window so old news does not accumulate forever.
- Stop retrying repeatedly failing clusters after a small attempt cap.
- Support a configurable English RSS source set with live-verified feeds.
- Schedule capture every 3-4 hours and analysis once per day.
- Demonstrate crash recovery and top-K behavior with fixture/stub evidence before implementation.

**Non-Goals:**
- No 9-dimensional attention scorer.
- No semantic/embedding ranking.
- No LLM-based screening.
- No representative-6 selection standard.
- No novelty/corroboration tuning.
- No cluster snapshot/member tables, attempts table, or complex backlog state machine.
- No early-signal reserved slot in this MVP.
- No changes to `analysis_orchestration`, `target_generation`, `llm_provider`, contract schemas, dedup, or `signal_clustering` internals.
- No CN direct sources/RSSHub in this change.
- No true GDELT integration in this change; the existing fixture adapter remains optional future work.

## Decisions

### D1 Configurable RSS Source Set

Use a small config file for source lists rather than hard-coded URLs. Proposed shape:

```json
[
  {
    "id": "rss:servethehome",
    "name": "ServeTheHome",
    "url": "https://www.servethehome.com/feed/",
    "enabled": true,
    "quality": "industry"
  }
]
```

Runtime lookup order:

1. `NEWS_RSS_SOURCES_FILE` if set.
2. `.local/rss_sources.json` if present.
3. `config/rss_sources.example.json` as a copyable template, not a production default with all feeds enabled.

Optional convenience env:

```text
NEWS_RSS_FEED_URLS=url1,url2
```

This is useful for quick smoke runs, but source ids/names are cleaner in the JSON file.

#### RSS Verification Evidence

Verified on 2026-06-12 with the current project `RssHttpFetcher(url)(None)`, not curl. "Alive" means fetch succeeded and the existing parser returned at least one item.

| Status | Source | Parsed Items | Latest Cursor | URL | First Parsed Title |
|---|---:|---:|---|---|---|
| alive | ServeTheHome | 6 | 2026-06-10T18:00:58Z | `https://www.servethehome.com/feed/` | Dell Pro Max 16 Plus Review A More Mobile NVIDIA RTX Pro 5000 Blackwell System |
| alive | The Register - headlines | 50 | 2026-06-11T14:32:57Z | `https://www.theregister.com/headlines.atom` | Apple version of Office 2019 becomes useless in a month |
| alive | Tom's Hardware - all | 50 | 2026-06-11T14:47:26Z | `https://www.tomshardware.com/feeds/all` | After spat with Chinese gov't, Meta cuts AI Manus off from its internal systems... |
| alive | EE Times | 10 | 2026-06-11T16:00:00Z | `https://www.eetimes.com/feed/` | GigaDevice Introduces GD32E512 and GD32E252 MCUs for Optical Modules |
| alive | SemiWiki | 5 | 2026-06-11T13:00:32Z | `https://semiwiki.com/feed/` | Technical Paper: FPGA Prototyping That Creates Useful PreSilicon Evidence |
| alive | TechPowerUp | 104 | 2026-06-11T13:09:20Z | `https://www.techpowerup.com/rss/news` | NVIDIA at Computex 2026: RTX Spark Gaming Hands-On, DLSS 4.5, and More |
| alive | EDN | 10 | 2026-06-11T12:00:53Z | `https://www.edn.com/feed/` | Memory card interfaces keep pace with the internal bus evolution race: Part 2 |

Dead or currently unsuitable with the current fetcher:

| Status | Source | URL | Current Failure |
|---|---|---|---|
| dead-error | SemiAnalysis | `https://semianalysis.com/feed/` | SSL unexpected EOF |
| dead-error | SemiAnalysis Substack | `https://semianalysis.substack.com/feed` | SSL unexpected EOF |
| dead-error | HPCwire | `https://www.hpcwire.com/feed/` | HTTP 403 |
| dead-error | AnandTech | `https://www.anandtech.com/rss/` | XML parse error |
| dead-error | Chips and Cheese | `https://chipsandcheese.com/feed/` | HTTP 403 |
| dead-error | StorageReview | `https://www.storagereview.com/feed/` | HTTP 403 |
| dead-error | CNX Software | `https://www.cnx-software.com/feed/` | HTTP 403 |
| dead-error | The Next Platform | `https://www.nextplatform.com/feed/` | read timeout |
| dead-error | Semiconductor Engineering | `https://semiengineering.com/feed/` | HTTP 403 |
| dead-error | Semiconductor Digest | `https://www.semiconductor-digest.com/feed/` | HTTP 403 |
| dead-error | Data Center Dynamics | `https://www.datacenterdynamics.com/en/rss/news/` | HTTP 403 |
| dead-error | Electronics Weekly | `https://www.electronicsweekly.com/feed/` | HTTP 403 |
| dead-error | EE News Europe | `https://www.eenewseurope.com/en/feed/` | HTTP 403 |
| dead-error | All About Circuits | `https://www.allaboutcircuits.com/news/rss/` | HTTP 403 |

Recommended initial enabled set for review:

- Enable by default: ServeTheHome, EE Times, SemiWiki, EDN.
- Keep optional/low-priority because broad or high-volume: The Register headlines, Tom's Hardware all, TechPowerUp.
- Exclude for this change: all dead-error feeds above.

GDELT: the project has a fixture-shaped adapter. True GDELT fetching can be a later source change if the RSS set proves too narrow.

### D2 Split Capture From Analyze

Add two operation paths:

```text
capture_sources(store, adapters) -> IngestionRunResult
analyze_pending(store, author, reviewer, proposer, price_lookup, *, top_k=5) -> PipelineResult
```

`capture_sources` is intentionally thin:

```text
run_once(store, adapters)
```

It does not call the clusterer, LLM, target generation, or digest.

`analyze_pending`:

1. reads accepted signals not marked analyzed;
2. clusters them with existing `DefaultSignalClusterer`;
3. applies cheap deterministic coarse ranking;
4. analyzes at most `top_k` clusters;
5. marks signals in successfully analyzed clusters as analyzed;
6. leaves everything else pending.

Existing `run_pipeline` can remain as a smoke/convenience wrapper, but live scheduled operation should use the split paths.

### D3 Minimal Pending Mechanism

Use one small table:

```sql
create table if not exists signal_analysis_state (
  signal_id text primary key,
  state text not null,
  attempts integer not null default 0,
  updated_at text not null
);
```

Pending means:

```sql
signals.id has no row in signal_analysis_state
```

Terminal states:

```text
analyzed
skipped_stale
skipped_failed
```

One non-terminal state is required to persist attempts below the failure cap:

```text
pending
```

Pending means either no row exists yet or the row has `state = 'pending'`. The three terminal states above remove a signal from future analysis.

This remains deliberately simpler than a full backlog/attempts table. It solves three correctness problems:

```text
capture succeeds -> process crashes -> next analyze still sees accepted signals as pending
pending grows without bound -> old rows become skipped_stale
one bad cluster fails repeatedly -> rows become skipped_failed
```

Marking rule:

- Mark signals analyzed after `analyze()` succeeds for their cluster.
- If target generation fails after a thesis is created, the signal has still been analyzed.
- If `analyze()` itself fails, increment `attempts` for every signal in the selected cluster.
- When a selected cluster reaches `max_attempts` (default 2), mark its signals `skipped_failed`.
- Before selecting clusters, mark pending signals older than `pending_max_age_days` (default 7) as `skipped_stale`; stale signals do not participate in clustering/ranking.

`pending_max_age_days` and `max_attempts` are configurable operation parameters. They are deliberately small, coarse safeguards rather than a full retry/backlog state machine.

### D4 Cheap Top-K Selection

The MVP selector should be intentionally small and deterministic. It must not attempt to infer full mechanism/transmission semantics; that is the LLM's job after selection.

Allowed cheap features:

- source quality: configured source tier, not LLM judgment;
- has number: digits, percentages, amounts, weeks/months, order/capacity terms;
- universe/watchlist keyword hit: simple company/supply-chain keyword dictionary;
- freshness: published time;
- generic penalty: title/body dominated by generic terms with no specific entity or number.

Explicitly out of scope:

- 9-dimensional scorer;
- novelty/corroboration tuning;
- representative-6 policy;
- embedding similarity;
- semantic transmission scoring;
- early-signal reserved slot.

Cluster score can be:

```text
max(signal_score in cluster) + small capped size bonus - generic penalty
```

Default:

```text
top_k = 5 clusters per analyze run
```

Unselected clusters are not errors. They simply remain pending.

### D5 Scheduling

Use two launchd jobs or two wrapper modes:

```text
capture: every 3-4 hours
analyze: once daily at 18:00 local time
```

Recommended first schedule:

```text
capture at 08:30, 12:30, 16:30, 21:30
analyze at 18:00
```

Rationale:

- Capture is cheap and keeps RSS cursors from missing short feeds.
- Analyze is bounded and runs after A-share close.
- Daily digest can be generated after analyze.

The implementation should avoid overlapping store writers. A simple operation-layer lock in the wrapper is acceptable if concurrent launchd runs are possible.

### D6 Fixture Cycle Evidence

An ad-hoc fixture run using existing `ContractStore`, `run_once`, `RssAtomAdapter`, `FixtureFetcher`, and `DefaultSignalClusterer` demonstrated the MVP pending model:

```text
capture1 accepted 2 pending 2
capture2 accepted 2 pending 4
after simulated crash/reopen pending 4
analyze1 {'pending_before': 4, 'candidate_clusters': 4, 'selected_clusters': 1, 'selected_signal_ids': [['sig-1']], 'pending_after': 3}
analyze2 {'pending_before': 3, 'candidate_clusters': 3, 'selected_clusters': 1, 'selected_signal_ids': [['sig-3']], 'pending_after': 2}
```

What this proves:

- Two independent capture runs can add accepted signals without triggering LLM analysis.
- Closing and reopening the store after capture leaves all accepted signals pending.
- Analyze reads pending from the store, not from a before/after diff.
- `top_k=1` is enforced.
- Already analyzed signals are not processed again.
- Remaining signals stay pending rather than being discarded.

This is sufficient evidence for the design gate. The implementation still needs formal tests after approval.

## Risks / Trade-offs

- [Risk] Repeated `analyze()` failure can leave the same cluster pending forever. -> Mitigation: accept for MVP; add attempt/error state only if it appears in real runs.
- [Risk] Cheap ranking may miss a subtle but important signal. -> Mitigation: keep every accepted signal pending until analyzed; run daily top-K; avoid deleting unselected items.
- [Risk] Broad feeds like Tom's Hardware and TechPowerUp may produce too much noise. -> Mitigation: keep source list configurable and start with a smaller enabled set.
- [Risk] Frequent capture can hit RSS source rate limits. -> Mitigation: 3-4 hour cadence is modest; source list is configurable; failed source fetches are already isolated.
- [Risk] SQLite write overlap between capture and analyze. -> Mitigation: schedule windows apart and add an operation-layer lock if implementation shows contention.

## Open Questions

- Which alive feeds should be enabled by default for the first live run: narrow set only, or include broad sources at low priority?
- Should `run_pipeline --pipeline` remain capture+analyze for manual smoke, or should it be deprecated in favor of explicit `--capture` and `--analyze`?
- Should a failed `analyze()` leave signals pending indefinitely in MVP, or should the single table include `last_error` while still avoiding a full attempts table?
