## Why

The live pipeline can now run end-to-end with a persistent store, but it is still manually triggered from an interactive shell. That shell currently supplies keys, proxy variables, RSS configuration, and a rich `PATH`. A scheduled runner such as launchd does not inherit those settings by default, so the main operational risk is "interactive run works, scheduled run fails."

This change operationalizes the pipeline as a self-contained scheduled run: source secrets at runtime, reproduce the DeepSeek proxy environment, use a stable persistent SQLite store, append redacted logs, and expose the launchd install/uninstall steps.

## What Changes

- Add a self-contained scheduled-run wrapper script for the live pipeline.
- The wrapper loads project-local `.local/runtime.env`, sources repo-external `~/.config/news-llm/keys.env` at runtime, and never writes keys into scripts, plist files, or logs.
- The wrapper exports proxy variables for DeepSeek and RSS configuration, then runs `scripts/run_live.py --pipeline --store .local/news-data/live-store.db` with an absolute Python path.
- The wrapper appends redacted output to `.local/news-data/logs/YYYY-MM-DD.log`.
- Add a launchd LaunchAgent design for a daily user-session run after A-share close.
- Document how to install, verify, disable, inspect logs, inspect the persistent store, and change feeds.

## Capabilities

### New Capabilities

- `scheduled-run`: operation-layer scheduled execution for the existing live pipeline.

### Modified Capabilities

- `persistent-store`: scheduled runs use the existing persistent store path and cumulative data semantics.

## Impact

- Affected files:
  - `scripts/run_scheduled.sh`
  - launchd plist under a repo-local location before installation
  - OpenSpec artifacts under `openspec/changes/operationalize-scheduled-run/`
  - tests for script/plist behavior where practical
- Explicitly not affected:
  - `news_contracts`
  - `pipeline_orchestration`
  - `analysis_orchestration`
  - `llm_provider`
  - `target_generation`
  - `market_data`
  - `signal_clustering`
  - `source_ingestion`

## Gate

Before installing launchd, the wrapper must pass a stripped-environment proof run:

```bash
env -i HOME="$HOME" PATH="/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin" bash scripts/run_scheduled.sh
```

The evidence must show the pipeline can still ingest, call DeepSeek, use real market data, persist rows, and finish with no pipeline errors.
