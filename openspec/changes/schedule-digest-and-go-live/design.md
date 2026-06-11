# Design: schedule-digest-and-go-live

## D1. Digest Runs Only After Successful Analysis

`scripts/run_scheduled.sh` remains the single environment wrapper for launchd. After `NEWS_RUN_MODE=analyze` or `NEWS_RUN_MODE=pipeline` completes with `rc=0`, it runs:

```bash
"$PYTHON_BIN" "$PROJECT_ROOT/scripts/generate_digest.py" --store "$STORE_PATH"
```

Capture mode does not generate a digest because it does not create theses or targets. If analysis fails, digest generation is skipped so the log reflects the failure rather than producing a stale or misleading daily note.

`generate_digest.py` already prints `markdown=` and `html=` paths. Those lines flow through the existing wrapper redactor and dated log.

## D2. Date Handling

The wrapper passes `--date "$(date -u +%F)"` to `generate_digest.py`. Stored thesis timestamps use UTC `track_record.created_at`, so the digest date should be UTC as well. At the normal 18:00 Asia/Shanghai schedule this matches the local calendar date, and manual after-midnight kickstarts still select the theses created by that launchd run.

## D3. Launchd Migration

The live machine should run exactly two user LaunchAgents:

- `com.wukong.news-capture`: capture-only, 08:30, 12:30, 16:30, 21:30.
- `com.wukong.news-analyze`: analyze + digest, 18:00.

The obsolete `com.wukong.news-pipeline` job is removed from the user LaunchAgents directory and unloaded with launchctl if present. The two checked-in plist templates are copied into `~/Library/LaunchAgents/` and loaded.

Verification uses real launchd, not only an interactive shell:

1. Trigger capture manually or verify pending signals exist.
2. Trigger `com.wukong.news-analyze` with `launchctl kickstart`.
3. Inspect `.local/news-data/logs/YYYY-MM-DD.log` for analysis state, real market data, digest paths, and `exit_code=0`.
4. Inspect the generated Markdown digest for Chinese research prose and compliance wording.

## D4. Documentation

The README and operations doc describe:

- Daily flow: capture four times, analyze once, digest generated after analyze.
- Store, log, and digest paths.
- How to inspect the store and open/copy the digest.
- How to paste into a WeChat public account editor.
- How to stop and remove the LaunchAgents.

Secrets remain outside the repo and are only sourced at runtime.
