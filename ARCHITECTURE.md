# News Alpha System Architecture

## North Star

- Coverage: global equity markets. A-share ideas are discovered primarily by reasoning from global structural information, not by crawling Chinese retail discussion sources.
- Cadence: weekly deep research, event-driven analysis for major triggers, and daily review feedback that feeds the weekly research loop.
- Automation: human-in-the-loop. The system proposes; the user decides.
- Product shape: personal alpha tool for self-use, not an over-productized SaaS workflow.

## Final System Shape

```text
┌───────────────────────── You / PM = human-in-the-loop ─────────────────────────┐
│ Review watchlist · decide buy/sell · inject/challenge theses · record decisions │
└──────────────▲──────────────────────────────────────────────┬──────────────────┘
       ④ proposed list                                        │ decision + review
                                                               ▼
 ┌────────┐ sig ┌──────────┐ the ┌────────────┐ tgt ┌──────────┐   ┌──────────┐
 │① intake │────▶│② gate     │────▶│③ analysis   │────▶│④ targets  │   │⑤ feedback │
 │global   │nal │provenance │sis │free body   │     │watchlist │   │daily raw │
 │sources  │    │dedup      │    │completeness│     │state     │   │maturity  │
 │+last30d │    │triage     │    │falsify     │     │logic/buy │   │calibrate │
 │attention│    │~90% cut   │    │global→A    │     │empty ok  │   │weekly in │
 └────────┘     └──────────┘     └────────────┘     └──────────┘   └──────────┘
      ▲              ▲                 ▲                │               │
      │              │                 │                │               │
 ┌────┴─────┐        │                 │                │               │
 │①b market │────────┘                 │                │               │
 │move scan │ market_move -> backtrace_news -> signal   │               │
 │after hrs │ event gate may trigger ③                 │               │
 └──────────┘                         │                │               │
      │                               │                │               │
      └──────────────┬────────────────┴────────────────┴───────────────┘
                     │ read / write
      ┌──────────────▼────────────────────────────────────────┐
      │ SQLite memory base (D6 feedback foundation)            │
      │ signals · theses · targets · track_record              │
      │ source_cursors · human_decisions · transmission_map     │
      └───────────────────────────────────────────────────────┘
```

## Cadence

- Daily: intake and gate write accepted signals; feedback records `outcome_raw`.
- Daily feedback maturity filter: only outcomes whose verification window has expired, event has occurred, or confidence is sufficient become `calibration_signal`.
- Event-driven: major source-backed signal or significant market move can trigger analysis immediately. Event triggers require a hard gate, a trigger budget, and a stored `trigger_reason`.
- Weekly: read touched themes from the week plus mature calibration signals, run analysis, update only touched themes, and perform one completeness scan. The weekly output may be an explicit empty recommendation with reasons.

## Analysis Layer

The analysis layer is intentionally light-structured:

1. Free-form thesis generation.
2. Completeness critique: ask what second-order impacts may be missing and produce candidate additional theses only.
3. Adversarial falsification: independent review instance and persona before confirmation.

The completeness critique is not a reasoning template and must not force the thesis body into fixed fields.

## Source Policy For A-Shares

- Discovery: global structural information, supply chains, policies, climate, bottlenecks, export controls, and market moves.
- Verification: official A-share materials are allowed, including CNINFO announcements, financial reports, and exchange inquiries.
- Excluded: Chinese retail sentiment sources such as Xueqiu, stock forums, and Weibo.

## Contracts

- Between ①/①b/② and downstream: `signal-contract`.
- Between ③ and ④: `thesis-contract`.
- Output of ④: `target-contract`.
- Feedback and human decision interfaces are part of the memory foundation in this change; full calibration engine and a dedicated `market-event-contract` are later changes.
