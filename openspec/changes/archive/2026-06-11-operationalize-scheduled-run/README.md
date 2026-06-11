# Scheduled News Pipeline Runbook

## What Runs

`launchd` runs:

```bash
/bin/bash /Users/wukong/mylife/news/scripts/run_scheduled.sh
```

The wrapper then runs:

```bash
python scripts/run_live.py --pipeline --store .local/news-data/live-store.db
```

The wrapper is the single place that loads `.local/runtime.env`, sources the repo-external key file, sets the DeepSeek proxy environment, sets the RSS feed, and redacts logs.

This repo is public. Real keys must live outside the repo:

```text
~/.config/news-llm/keys.env
```

The wrapper creates the parent directory if needed, but the key file itself must be created by the operator and chmodded to `600`.

After a successful pipeline run, the wrapper also appends `--show-store` output to the same dated log. Set `NEWS_SHOW_STORE_AFTER_RUN=0` to disable that summary.

## Schedule

The LaunchAgent label is:

```text
com.wukong.news-pipeline
```

It runs daily at 18:00 local time, after A-share close. To change the time, edit `Hour` and `Minute` in:

```text
/Users/wukong/mylife/news/launchd/com.wukong.news-pipeline.plist
```

then reinstall the plist.

## Persistent Data

Directory layout:

| Kind | Path | Git status |
|---|---|---|
| API keys | `~/.config/news-llm/keys.env` | outside repo |
| Runtime overrides | `.local/runtime.env` | gitignored |
| Store | `.local/news-data/live-store.db` | gitignored |
| Logs | `.local/news-data/logs/YYYY-MM-DD.log` | gitignored |

Store:

```text
.local/news-data/live-store.db
```

Logs:

```text
.local/news-data/logs/YYYY-MM-DD.log
```

Approximate run cost/time depends on new RSS items and generated clusters. A 6-item ServeTheHome run has taken a few minutes because each cluster can call DeepSeek for analysis, review, and target proposal.

## First-Time Setup

Create keys outside the public repo:

```bash
mkdir -p "$HOME/.config/news-llm"
chmod 700 "$HOME/.config/news-llm"
$EDITOR "$HOME/.config/news-llm/keys.env"
chmod 600 "$HOME/.config/news-llm/keys.env"
```

Required:

```text
DEEPSEEK_API_KEY=...
TUSHARE_TOKEN=...
```

Optional:

```text
RELAY_API_KEY=...
RELAY_BASE_URL=...
RELAY_FORMAT=...
RELAY_MODEL=...
RELAY_JSON_MODE=...
```

Create local runtime overrides:

```bash
mkdir -p .local
cp config/runtime.env.example .local/runtime.env
chmod 600 .local/runtime.env
```

## Inspect Outputs

From `/Users/wukong/mylife/news`:

```bash
python scripts/run_live.py --show-store .local/news-data/live-store.db
```

Recent log:

```bash
tail -200 .local/news-data/logs/$(date +%F).log
```

## Change Feed

For a one-off run:

```bash
NEWS_RSS_FEED_URL="https://example.com/feed.xml" bash scripts/run_scheduled.sh
```

For the scheduled run, update the wrapper default or add a reviewed LaunchAgent environment override. Future feeds can be Chinese, supply-chain focused, or multi-source once that operation policy is approved.

## Runtime Environment Variables

| Variable | Purpose | Default |
|---|---|---|
| `NEWS_CONFIG_FILE` | Optional runtime override file | `.local/runtime.env` |
| `NEWS_KEYS_FILE` | Repo-external key file | `~/.config/news-llm/keys.env` |
| `NEWS_STORE_PATH` | SQLite store | `.local/news-data/live-store.db` |
| `NEWS_LOG_DIR` | Redacted logs | `.local/news-data/logs` |
| `NEWS_RSS_FEED_URL` / `RSS_FEED_URL` | RSS feed | `https://www.servethehome.com/feed/` |
| `NEWS_PYTHON` | Python executable for launchd | Homebrew Python, then `python3` fallback |
| `NEWS_HTTP_PROXY` | Proxy for DeepSeek/OpenAI-compatible calls | `http://127.0.0.1:6152` |
| `NEWS_SHOW_STORE_AFTER_RUN` | Append store summary after successful run | `1` |

## Install

```bash
mkdir -p "$HOME/Library/LaunchAgents"
cp /Users/wukong/mylife/news/launchd/com.wukong.news-pipeline.plist "$HOME/Library/LaunchAgents/"
launchctl load "$HOME/Library/LaunchAgents/com.wukong.news-pipeline.plist"
launchctl list | grep com.wukong.news-pipeline
```

Manual verification:

```bash
launchctl kickstart "gui/$(id -u)/com.wukong.news-pipeline"
tail -200 .local/news-data/logs/$(date +%F).log
```

## Stop

```bash
launchctl unload "$HOME/Library/LaunchAgents/com.wukong.news-pipeline.plist"
rm "$HOME/Library/LaunchAgents/com.wukong.news-pipeline.plist"
```
