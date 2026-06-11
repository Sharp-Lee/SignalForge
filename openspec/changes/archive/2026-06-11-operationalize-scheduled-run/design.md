## Context

The live pipeline already works when started manually:

```bash
set -a; source ~/.config/news-llm/keys.env; set +a
export RSS_FEED_URL="https://www.servethehome.com/feed/"
python scripts/run_live.py --pipeline --store .local/news-data/live-store.db
```

For GitHub publication, the scheduled wrapper now keeps secrets outside the repo and stores non-secret runtime state under `.local/`.

The operational risk is that launchd and cron do not inherit the interactive shell environment. In this project, that environment matters:

- API keys are sourced from `~/.config/news-llm/keys.env` by default, after optional `.local/runtime.env` overrides are loaded.
- DeepSeek succeeds in the interactive environment with local proxy variables.
- Market data providers are scoped to bypass the proxy inside `market_data`.
- Scheduled jobs have a minimal `PATH` and do not source user shell startup files reliably.

## R1 Wrapper Design

Add `scripts/run_scheduled.sh` as the single scheduled entry point.

Default configuration:

- project: resolved from the script path;
- runtime config: `.local/runtime.env`;
- key file: `~/.config/news-llm/keys.env`;
- store: `.local/news-data/live-store.db`;
- logs: `.local/news-data/logs/YYYY-MM-DD.log`;
- feed: `https://www.servethehome.com/feed/`;
- Python: `/opt/homebrew/opt/python@3.12/libexec/bin/python3`, falling back to `python3` from `PATH`;
- proxy: `http://127.0.0.1:6152` exported as `HTTP_PROXY`, `HTTPS_PROXY`, `http_proxy`, and `https_proxy`.

Override knobs:

- `NEWS_KEYS_FILE`
- `NEWS_STORE_PATH`
- `NEWS_LOG_DIR`
- `NEWS_RSS_FEED_URL` or `RSS_FEED_URL`
- `NEWS_PYTHON`
- `NEWS_HTTP_PROXY`

The script:

1. creates the store parent directory and log directory;
2. sources the key file with `set -a` so required provider variables are exported;
3. exports proxy variables for DeepSeek;
4. exports `RSS_FEED_URL`;
5. runs:

```bash
"$PYTHON_BIN" "$PROJECT_ROOT/scripts/run_live.py" --pipeline --store "$STORE_PATH"
```

On success, it also appends:

```bash
"$PYTHON_BIN" "$PROJECT_ROOT/scripts/run_live.py" --show-store "$STORE_PATH"
```

This makes no-new-signal scheduled runs still operationally useful: the log shows cumulative thesis/target state and real `price_change_since_signal` values from the persistent store. It can be disabled with `NEWS_SHOW_STORE_AFTER_RUN=0`.

All output is passed through:

```bash
sed -E 's/sk-[A-Za-z0-9_-]{10,}/***REDACTED***/g'
```

and appended with `tee -a` to the dated log. The underlying `run_live.py` redactor also masks known key values, including `TUSHARE_TOKEN`.

## R1 Stripped Environment Evidence

The following evidence predates the later repo-public hardening that moved the default key path back outside the repo and the default store/log paths under `.local/`. It remains as the original launchd-environment proof; current verification is repeated after hardening.

Command:

```bash
env -i HOME="$HOME" PATH="/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin" bash scripts/run_scheduled.sh
```

Result: passed. The wrapper ran with no inherited interactive env other than `HOME` and minimal `PATH`.

Key redacted stdout:

```text
scheduled news pipeline start: 2026-06-11T06:08:49Z
project_root=/Users/wukong/mylife/news
store=/Users/wukong/news-data/live-store.db
feed=https://www.servethehome.com/feed/
log=/Users/wukong/news-data/logs/2026-06-11.log
python=/opt/homebrew/opt/python@3.12/libexec/bin/python3
proxy=enabled
→ pipeline=deepseek  source=rss:live  feed=https://www.servethehome.com/feed/
→ market_data=REAL  universe_source=tushare  symbols=40
→ store=/Users/wukong/news-data/live-store.db
```

Ingestion and persistence:

```text
PIPELINE INGESTION
source rss:live:
  accepted : 6
  rejected : 0
  errors   : []
new_signal_count: 6

STORE COUNTS
  signals      : 6
  theses       : 6
  targets      : 9
  track_record : 6
thesis_count: 6
```

Real price evidence:

```text
PIPELINE TARGETS
price layer = REAL
universe source = tushare
target #1
  symbol   : 300308.SZ
  name     : 中际旭创
  price_change_since_signal: -0.006917808812197516
  priced_in     : {"price_change_since_signal": -0.006917808812197516, "risk": "low"}
  validate_target.accepted = True

target #6
  symbol   : 688525.SH
  name     : 佰维存储
  price_change_since_signal: 0.03883336064230714
  priced_in     : {"price_change_since_signal": 0.03883336064230714, "risk": "low"}
  validate_target.accepted = True
```

Failure status:

```text
PIPELINE ERRORS
errors: []
scheduled news pipeline exit_code=0
```

Conclusion: the stripped-environment risk is handled by the wrapper. It successfully sourced keys, reproduced the proxy environment for DeepSeek, used Tushare real market data, wrote to the persistent store, and produced redacted logs.

## R2 Launchd Design After Gate Approval

Use a macOS user LaunchAgent so the job runs in the user session where the local proxy application is expected to be available.

Plist label:

```text
com.wukong.news-pipeline
```

Planned schedule:

```xml
<key>StartCalendarInterval</key>
<dict>
  <key>Hour</key><integer>18</integer>
  <key>Minute</key><integer>0</integer>
</dict>
```

The plist runs:

```text
/bin/bash /Users/wukong/mylife/news/scripts/run_scheduled.sh
```

It should not contain API keys. It may contain only static paths and scheduler metadata.

Install:

```bash
mkdir -p "$HOME/Library/LaunchAgents"
cp /Users/wukong/mylife/news/launchd/com.wukong.news-pipeline.plist "$HOME/Library/LaunchAgents/"
launchctl load "$HOME/Library/LaunchAgents/com.wukong.news-pipeline.plist"
launchctl list | grep com.wukong.news-pipeline
```

Disable:

```bash
launchctl unload "$HOME/Library/LaunchAgents/com.wukong.news-pipeline.plist"
rm "$HOME/Library/LaunchAgents/com.wukong.news-pipeline.plist"
```

Manual launchd verification:

```bash
launchctl kickstart "gui/$(id -u)/com.wukong.news-pipeline"
tail -200 .local/news-data/logs/$(date +%F).log
```

## Operator Workflow

Inspect accumulated store:

```bash
python scripts/run_live.py --show-store .local/news-data/live-store.db
```

Inspect logs:

```bash
tail -200 .local/news-data/logs/$(date +%F).log
```

Change feed without architecture changes:

```bash
NEWS_RSS_FEED_URL="https://example.com/feed.xml" bash scripts/run_scheduled.sh
```

After launchd installation, a durable feed override can be added to the wrapper configuration or plist environment if the reviewer approves that operational shape.

## Non-Goals

- No changes to the pipeline, contracts, analysis, target generation, market data, signal clustering, or ingestion internals.
- No feedback calibration implementation.
- No multi-feed scheduler.
- No launchd installation before R1 approval.

## Public Repo Secret Hardening

After the repository became public, real keys were moved back out of the repository working tree. The wrapper now defaults to:

```text
NEWS_KEYS_FILE=$HOME/.config/news-llm/keys.env
NEWS_STORE_PATH=.local/news-data/live-store.db
NEWS_LOG_DIR=.local/news-data/logs
```

`.local/` remains gitignored and is acceptable for non-secret runtime state such as SQLite stores and logs. Real keys must not live in `.local/` or any other repo path.

The wrapper creates:

- the key-file parent directory;
- the store parent directory;
- the log directory.

If the key file itself is missing, the wrapper exits clearly and points to `config/runtime.env.example` and this runbook.

Verification after hardening:

```text
repo_key_exists=no
home_key_exists=yes
home_key_mode=600
deepseek_lines=1
tushare_lines=1
runtime_external_key_lines=1
```

Stripped-environment proof command:

```bash
env -i HOME="$HOME" PATH="/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin" \
  NEWS_STORE_PATH="/tmp/relocate-verify-87990.db" \
  bash scripts/run_scheduled.sh
```

Key evidence:

```text
store=/tmp/relocate-verify-87990.db
runtime_config=/Users/wukong/mylife/news/.local/runtime.env
→ market_data=REAL  universe_source=tushare  symbols=40
PIPELINE INGESTION
  accepted : 6
STORE COUNTS
  signals      : 6
  theses       : 6
  targets      : 11
  track_record : 6
PIPELINE ERRORS
errors: []
scheduled news pipeline exit_code=0
```

A follow-up run against the same temporary store verified process exit status and store-summary output:

```text
verify_exit_code=0
TARGETS
- symbol=688525.SH name=佰维存储 logic_score=70 buy_point=neutral priced_in=medium price_change_since_signal=0.12398613518197567
```

The temporary verification database was removed after the run.
