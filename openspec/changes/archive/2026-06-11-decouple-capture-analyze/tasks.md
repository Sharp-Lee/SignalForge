## 1. Planning

- [x] 1.1 Update design with stale/failed terminal states
- [x] 1.2 Add delta specs for capture/analyze flow, source feed set, pipeline orchestration, and scheduled run
- [x] 1.3 Validate `decouple-capture-analyze` with OpenSpec strict mode before implementation

## 2. Pending State And Pipeline Split

- [x] 2.1 Add minimal `signal_analysis_state` table creation and helpers
- [x] 2.2 Implement `capture_sources(store, adapters)` as a thin ingestion wrapper
- [x] 2.3 Implement `pending_signals()`, stale expiry, attempts increment, and terminal state marking
- [x] 2.4 Implement `analyze_pending(...)` using existing clusterer, analyze, and target generation
- [x] 2.5 Enforce `top_k`, `pending_max_age_days`, and `max_attempts`
- [x] 2.6 Keep `run_pipeline` as manual smoke composition while routing through pending-state logic

## 3. Source Configuration

- [x] 3.1 Add configurable RSS source loading
- [x] 3.2 Add narrow example source config with ServeTheHome, EE Times, SemiWiki, and EDN enabled
- [x] 3.3 Keep broad/high-volume feeds disabled by default

## 4. Operation Scripts And Scheduling

- [x] 4.1 Add explicit capture and analyze modes to the operation script
- [x] 4.2 Update scheduled wrapper to run capture/analyze modes
- [x] 4.3 Add launchd plist(s) for capture 4x/day and analyze daily at 18:00
- [x] 4.4 Print pending, selected, analyzed, skipped stale, and skipped failed counts

## 5. Tests And Evidence

- [x] 5.1 Add offline test for capture x2 then analyze pending without duplicate analysis
- [x] 5.2 Add offline test for crash recovery after capture
- [x] 5.3 Add offline test for top-K leaving the rest pending
- [x] 5.4 Add offline test for stale pending becoming `skipped_stale`
- [x] 5.5 Add offline test for repeated analysis failure becoming `skipped_failed`
- [x] 5.6 Add offline test for source config loading and narrow defaults
- [x] 5.7 Run `python -m pytest tests/ -q`
- [x] 5.8 Run `openspec validate decouple-capture-analyze --strict`
- [x] 5.9 Run small live capture/analyze proof and report redacted stdout
