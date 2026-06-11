# Project Context

## North Star

- Coverage: global equity markets. A-share ideas are discovered mainly by reasoning from global structural information, not by crawling Chinese retail discussion sources.
- Cadence: weekly deep research, event-driven analysis, and daily review feedback that feeds the weekly loop.
- Automation: human-in-the-loop. The system proposes; the user decides.
- Product shape: personal alpha tool for self-use, not an over-productized product.

## System Shape

```text
① intake(global sources + last30days attention)
①b market move scan(after-hours reverse intake)
  -> ② gate(provenance, dedup, triage)
  -> ③ analysis(free-form generation, completeness critique, adversarial falsification)
  -> ④ targets(watchlist, state machine, logic_score and buy_point, empty recommendation allowed)
  -> ⑤ feedback(outcome_raw, maturity filter, calibration_signal)
  -> SQLite memory(signals, theses, targets, track_record, source_cursors, human_decisions, transmission_map)
  -> human-in-the-loop review and decisions
```

## Key Architecture Decisions

- Reverse intake is an independent after-hours module: `market_move -> backtrace_news -> signal(signal_origin = market_move)`. It can trigger event-level analysis but is not a real-time trading engine.
- Analysis has three steps: free-form thesis generation, completeness critique, and adversarial falsification.
- Feedback is a core daily loop. Daily review writes `outcome_raw`; only mature evidence becomes `calibration_signal` for weekly research.
- Event-driven analysis requires hard gates, trigger budget, and persisted `trigger_reason`.
- Weekly research updates touched themes incrementally and runs one completeness scan instead of full recomputation.
- A-share discovery comes from global structural information. A-share official filings and exchange materials may be used for verification; retail sentiment sources are excluded.
- Empty recommendations are valid output when no opportunity clears the bar.

## Contract Placement

- `signal-contract`: accepted input from intake, reverse intake, and last30days attention.
- `thesis-contract`: free-form causal thesis plus cross-market transmission metadata extracted after the body.
- `target-contract`: investable target view linked to confirmed theses.
- Feedback and human decisions are memory-layer interfaces. Full calibration and a dedicated market-event contract are future changes.
