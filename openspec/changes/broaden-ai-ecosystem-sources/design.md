## Context

The current scheduled pipeline can already tolerate broader capture volume because capture and analyze are decoupled: capture persists accepted signals, analyze reads pending signals, clusters them, and processes only a top-K budget per run. That makes source breadth a capture-quality problem rather than a single-run timeout problem.

The existing default RSS list is still biased toward servers, semiconductors, broad market feeds, and investment commentary. The user wants AI ecosystem coverage across hardware, energy/power, technology, and software so the system can discover transmission chains such as "AI data center growth -> grid equipment / power electronics / cooling / storage demand -> A-share beneficiaries."

Live probing with the planned browser user agent and the project's RSS parser produced this source evidence:

| Source | Domain | URL | Result | Notes |
| --- | --- | --- | --- | --- |
| ServeTheHome | hardware | `https://www.servethehome.com/feed/` | existing live | keep |
| EE Times | hardware | `https://www.eetimes.com/feed/` | existing live | keep |
| SemiWiki | hardware | `https://semiwiki.com/feed/` | existing live | keep |
| EDN | hardware | `https://www.edn.com/feed/` | existing live | keep |
| Semiconductor Engineering | hardware | `https://semiengineering.com/feed/` | 200, 10 parsed | browser UA unlocks a high-value source |
| The Next Platform | hardware | `https://www.nextplatform.com/feed/` | 200, 1 parsed | keep; low parsed count is acceptable |
| Utility Dive | energy | `https://www.utilitydive.com/feeds/news/` | 200, 10 parsed | grid/utility coverage |
| PV Magazine | energy | `https://www.pv-magazine.com/feed/` | 200, 10 parsed | solar/power transition coverage |
| Power Electronics News | energy | `https://www.powerelectronicsnews.com/feed/` | 200, 10 parsed | power semiconductor/electronics coverage |
| Data Center Knowledge | energy | `https://www.datacenterknowledge.com/rss.xml` | 200, 50 parsed | data-center infrastructure coverage |
| Energy Storage News | energy | `https://www.energy-storage.news/feed/` | 200, 50 parsed | storage/grid bottleneck coverage |
| VentureBeat AI | ai_tech | `https://venturebeat.com/category/ai/feed/` | 200, 7 parsed | AI software/adoption coverage |
| IEEE Spectrum | ai_tech | `https://spectrum.ieee.org/feeds/feed.rss` | 200, 30 parsed | engineering/AI/data-center coverage |
| MIT Technology Review AI | ai_tech | `https://www.technologyreview.com/topic/artificial-intelligence/feed/` | 200, 10 parsed | AI research/product context |
| AI News | ai_tech | `https://www.artificialintelligence-news.com/feed/` | 200, 12 parsed | AI software/adoption coverage |
| InfoQ AI/ML/Data | ai_tech | `https://feed.infoq.com/ai-ml-data-eng/` | 200, 15 parsed | developer/platform coverage |
| Data Center Dynamics | energy | `https://www.datacenterdynamics.com/en/rss/` | 403 | exclude |
| Data Center Frontier | energy | `https://www.datacenterfrontier.com/rss.xml` | 403 | exclude |
| Power Grid International | energy | `https://www.power-grid.com/feed/` | 403 | exclude |
| HPCwire | hardware | `https://www.hpcwire.com/feed/` | 403 | exclude |
| InsideHPC | hardware | `https://insidehpc.com/feed/` | TLS handshake failure | exclude |
| The Verge AI | ai_tech | `https://www.theverge.com/rss/ai-artificial-intelligence/index.xml` | 200, 0 parsed | exclude until parser supports this shape |
| Renewable Energy World | energy | `https://www.renewableenergyworld.com/feed/` | 403 | exclude |
| SDxCentral | ai_tech | `https://www.sdxcentral.com/feed/` | 404 | exclude |

## Goals / Non-Goals

**Goals:**

- Remove the unused OpenBB change artifacts.
- Make the default RSS HTTP fetcher present a browser-like User-Agent.
- Broaden the committed source configuration across hardware, energy, and AI technology/software.
- Add domain metadata for source review and future reporting while keeping existing configs backward-compatible.
- Update the cheap signal scorer so energy/data-center/power/software signals can compete for top-K analysis.
- Verify the widened source set with a real capture run against a temporary store.

**Non-Goals:**

- Do not change LLM analysis, target generation, contracts, digest generation, market data, dedup, or clustering internals.
- Do not add OpenBB or any new external package.
- Do not implement a new ranking model, semantic scorer, or feed-quality calibration system.
- Do not archive this change before review.

## Decisions

### D1. Browser User-Agent at the default RSS transport boundary

`RssHttpFetcher` already supports injectable HTTP transport for tests. The production default `_default_http_get()` should use `urllib.request.Request` with a browser-like User-Agent and conservative Accept header. Tests that inject `http_get` remain offline and unaffected.

Alternative: configure per-source headers. Rejected for now because the verified failure mode is broad enough and a normal browser UA is harmless for existing feeds.

### D2. Source config gains optional `domain`

`RssSourceConfig` should add a `domain` field with a default such as `general`. Config files can mark `hardware`, `energy`, `ai_tech`, `markets`, `macro`, or `investing`. Existing config files without `domain` continue to load.

Alternative: encode domain inside `quality`. Rejected because quality and domain answer different questions: trust/volume vs ecosystem area.

### D3. Enable verified AI ecosystem sources by default

The example config should enable the verified hardware, energy, and AI technology feeds listed above. Dead, 403, TLS-failing, and parser-empty sources stay absent or disabled. The pending backlog and top-K analyzer are the intended load control mechanism.

High-volume but relevant feeds such as Data Center Knowledge and Energy Storage News are acceptable because this change changes capture breadth, not analyze budget.

### D4. Cheap scorer expands only as a coarse input-side priority hint

The scorer is not a thesis engine. It only prevents obvious infrastructure signals from starving under the top-K cap. Add lightweight terms such as `grid`, `energy`, `electric`, `power grid`, `solar`, `data center`, `cooling`, `megawatt`, `utility`, `storage`, `inference`, `agent`, and `software`.

Alternative: add a multi-dimensional scoring model. Rejected as overbuilt; the current architecture deliberately leaves mechanism/transmission reasoning to the LLM after deterministic input narrowing.

### D5. OpenBB removal is cleanup, not a replacement decision

`openspec/changes/add-openbb-research-adapter/` was never implemented or archived. Removing it keeps planning state aligned with the current direction: broaden live source capture first, revisit OpenBB only if there is a concrete adapter request later.

## Risks / Trade-offs

- [More noise from broader feeds] -> keep analyze top-K budget and pending backlog; use domain metadata for later source review.
- [Some feeds still block despite browser UA] -> only enable sources verified with the project parser; list excluded candidates.
- [Initial capture can be large] -> this is expected on a fresh store; persistent cursors make later captures incremental.
- [Cheap scorer can bias source selection] -> only add broad infrastructure keywords, not business logic or semantic scoring.

## Migration Plan

1. Delete the unused OpenBB change directory.
2. Add browser UA headers to the default RSS HTTP transport.
3. Add `domain` support to RSS source config and broaden the example source list.
4. Add regression tests for UA/default config/domain and expanded scorer terms.
5. Run full tests and `openspec validate broaden-ai-ecosystem-sources --strict`.
6. Run one real capture against a temporary store and report per-source accepted counts and sample titles across domains.
