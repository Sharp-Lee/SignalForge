## Context

The source set now captures the broad AI ecosystem: hardware, semiconductors, power/energy, data centers, cooling, storage, AI software, markets, and macro commentary. Capture can produce hundreds of pending signals, while `analyze_pending()` currently does:

1. read pending signals;
2. cluster them with `DefaultSignalClusterer`;
3. call `_select_top_clusters(clusters, top_k)`;
4. run `analyze()` and `propose_targets()` on selected clusters.

The existing `_select_top_clusters()` uses deterministic keyword scoring. It is useful as a safe fallback, but it is now too coarse as the primary selector: it can miss high-value cross-domain signals and over-select generic keyword-rich noise.

This change adds one small LLM triage call before expensive ③/④ analysis. The LLM chooses which clusters are worth deep analysis; if the LLM path fails, the existing keyword top-K selector still runs.

## Goals / Non-Goals

**Goals:**

- Replace direct keyword top-K selection in `analyze_pending()` with LLM cluster triage when a triage selector is configured.
- Keep `_select_top_clusters()` as mandatory fallback.
- Bound triage input by recency when there are too many pending clusters.
- Add strict triage schema/enforcement so hallucinated cluster ids fail closed.
- Persist selected-cluster reasons so later reporting can explain "why this signal was chosen."
- Prove the shape with one real DeepSeek triage probe over real captured RSS signals.

**Non-Goals:**

- Do not change `analysis_orchestration.analyze()`.
- Do not change `target_generation.propose_targets()`.
- Do not change contract schemas, digest rendering, market data, dedup, clustering, or RSS capture.
- Do not build a complex scoring system, multi-step agent, embedding search, or long-running ranking pipeline.
- Do not remove keyword scoring; it remains the deterministic fallback.

## Decisions

### D1. Triage replaces cluster selection, not analysis

`analyze_pending()` should keep clustering as-is, then choose clusters through a new selection path:

```text
pending signals
  -> DefaultSignalClusterer.cluster()
  -> select_clusters_for_analysis()
       if triage selector configured:
           newest candidate window -> LLM triage -> enforce -> selected clusters + reasons
       else or on any failure/empty:
           _select_top_clusters(clusters, top_k)
  -> existing analyze()
  -> existing propose_targets()
```

Implementation shape after approval:

- Add optional parameters to `analyze_pending()` and `run_pipeline()` such as:
  - `triage_selector=None`
  - `triage_candidate_limit=200`
- Keep the current function `_select_top_clusters()` unchanged as fallback.
- Add a small internal helper such as `_select_clusters_with_triage_or_fallback()`.

The triage selector should only return cluster ids and reasons. It must not create thesis content, target content, scores, or persistence-side contract objects.

### D2. Triage LLM call is a new provider role with strict schema

Add a new llm-provider role rather than embedding ad hoc prompt code inside `pipeline_orchestration`.

Prompt intent:

```text
You are SignalForge's cluster triage reviewer.
Select clusters that have real tradeable value for an AI ecosystem -> A-share personal alpha research system.
Prefer signals with possible transmission through supply/demand, price, orders, capacity, capex, regulation, energy/grid,
data centers, cooling, optical modules, power electronics, software adoption, or other investable chain effects.
Exclude generic commentary, market chatter, vendor marketing, pure product reviews, duplicate news, and broad tech opinion.
Reasons must be Simplified Chinese.
Only use cluster_id values from the supplied candidate list.
```

Output schema:

```json
{
  "title": "cluster_triage",
  "type": "object",
  "additionalProperties": false,
  "required": ["selected"],
  "properties": {
    "selected": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["cluster_id", "reason"],
        "properties": {
          "cluster_id": {"type": "string"},
          "reason": {"type": "string"}
        }
      }
    }
  }
}
```

Enforcement:

- `selected` must be an array.
- every `cluster_id` must be in the supplied candidate id set;
- reason must be non-empty Chinese prose;
- duplicate cluster ids are de-duped while preserving order;
- after enforcement, output is truncated to `top_k`;
- any hallucinated `cluster_id`, malformed shape, or empty/invalid reason raises `LlmProviderError`.

Triage enforcement follows the existing fail-closed provider style. Invalid triage output returns no partial selection to the pipeline; the pipeline catches the error and falls back to keyword top-K.

### D3. Candidate range is capped by freshness, not keyword value

The triage prompt must not grow without bound. When pending clusters exceed `triage_candidate_limit`, the system should sort clusters by `max(source.published_at)` descending and pass only the newest N clusters to triage.

Default recommendation: `triage_candidate_limit = 200`.

Rationale:

- It keeps the prompt under the DeepSeek context budget with compact cluster summaries.
- It avoids reintroducing crude keyword value judgment before triage.
- Older unselected clusters remain pending until normal stale expiry handles them.
- The real probe below sent 161 clusters and used 43,657 input tokens. A 200-cluster cap is still viable if summaries stay compact.

Each candidate should be compact:

```json
{
  "cluster_id": "cluster-121",
  "newest_at": "2026-06-11T12:40:07Z",
  "signal_count": 1,
  "cluster_reason": "singleton",
  "signals": [
    {
      "signal_id": "...",
      "source": "The Register",
      "published_at": "...",
      "title": "...",
      "summary": "first ~300 chars only"
    }
  ]
}
```

For multi-signal clusters, send only a small number of representative/newest signals, for example first 3 by published time. Triage should choose clusters, not consume full article bodies.

### D4. Fallback makes selection non-fatal

Fallback triggers:

- transport error;
- invalid JSON;
- schema/enforce failure;
- hallucinated cluster id;
- empty `selected`;
- no triage selector configured.

Fallback result:

```text
selected_clusters = _select_top_clusters(clusters, top_k)
triage_mode = "fallback_keyword"
```

This preserves the current deterministic behavior. Selection must never cause an analyze run to fail entirely.

### D5. Triage reason lands in analysis state

Reason should be persisted because it is useful for "为什么选这条" in later review/digest work.

Minimal storage decision:

- extend `signal_analysis_state` with nullable `triage_reason text`;
- when a selected cluster is processed, write the same reason onto all signals in that cluster;
- if the cluster later succeeds, the `analyzed` rows retain the reason;
- if the cluster fails below attempt cap and remains pending, the reason remains available for debugging/retry context.

Alternative considered: create a new triage decision table. Rejected for now because this change should stay small and the existing analysis-state table already tracks per-signal analysis lifecycle.

## Real Probe

Probe shape:

- Temporary store.
- Real RSS capture with current broad source set.
- `DefaultSignalClusterer`.
- DeepSeek `deepseek-chat` through `OpenAICompatibleCompletion(json_mode="object")`.
- `top_k = 5`.
- `triage_candidate_limit = 200`.
- Candidate ordering: newest cluster first by max `source.published_at`.
- No keyword pre-filter before triage.
- Cost estimate uses official DeepSeek `deepseek-chat` cache-miss upper-bound pricing: input `$0.27 / 1M`, output `$1.10 / 1M`. If prompt-cache hits apply, actual cost is lower.

Capture:

```text
capture_sources=21
accepted signals=334
pending_signals=334
total_clusters=161
supplied_candidates=161
```

Selected clusters:

```text
selected_1 cluster-156
source: Energy Storage News
title : RWE officially opens Australia’s first 8-hour battery storage system
reason: 澳大利亚首个8小时电池储能系统投运，直接反映储能时长需求提升，利好A股储能系统集成商及长时储能技术标的。

selected_2 cluster-121
source: The Register
title : Oracle's AI datacenter splurge gives investors the capex jitters
reason: Oracle AI数据中心资本开支达700亿美元，直接传导至AI基础设施供应链，利好A股光模块、服务器、电源、冷却等环节。

selected_3 cluster-092
source: The Register
title : Datacenter growth may run into a power wall by 2030
reason: 报告称数据中心增长可能在2030年前遭遇电力瓶颈，电力供应紧张将利好A股电网设备、储能及能源管理板块。

selected_4 cluster-109
source: Data Center Knowledge
title : Will Co-Packaged Optics Transform Data Centers?
reason: 共封装光学（CPO）有望变革数据中心，若突破将提升A股光模块与硅光器件板块的估值预期。

selected_5 cluster-003
source: Data Center Knowledge
title : Modine’s $4B Deal Turns Cooling Capacity into Reserved Infrastructure
reason: Modine收购案凸显冷却产能被提前预订，AI冷却需求确定性增强，利好A股液冷、温控设备供应商。
```

Usage:

```text
model=deepseek-chat
role=cluster_triage
input_tokens=43657
output_tokens=254
latency_ms=6141
stop=stop
estimated_usd_cache_miss_upper_bound=0.012067
```

Assessment:

- The selection is materially better than plain keyword ranking because it chose cross-domain tradable bottlenecks: long-duration storage, AI data-center capex, power wall, CPO, and cooling capacity.
- Reasons are Chinese and directly explain the A-share transmission logic.
- One call is cheap enough to run once per daily analyze cycle.
- Prompt size is already large at 161 clusters; the 200-cluster cap and compact summaries are necessary.

## Risks / Trade-offs

- [LLM selects plausible but low-quality clusters] -> keep reasons visible and retain keyword fallback; later review can compare selected clusters against outcomes.
- [LLM output hallucinates ids] -> provider enforce rejects entire triage and falls back.
- [LLM call fails or times out] -> fallback keyword selector preserves current behavior.
- [Prompt cost grows with capture breadth] -> cap candidates by freshness, compact signal summaries, and keep top-K small.
- [Reason persistence adds schema drift risk] -> store reason only in `signal_analysis_state`, not canonical thesis/target contracts.

## Migration Plan

If approved:

1. Add triage prompt/schema/enforcement to `llm_provider`.
2. Add a small triage selector wrapper with injected `Completion` transport.
3. Add optional triage selection parameters to `analyze_pending()` and `run_pipeline()`.
4. Add `triage_reason` nullable column to `signal_analysis_state` with idempotent migration.
5. Add fallback behavior and offline tests.
6. Run real `--analyze` against the live store and verify logs show triage selected clusters, reasons, thesis generation, and digest generation.
