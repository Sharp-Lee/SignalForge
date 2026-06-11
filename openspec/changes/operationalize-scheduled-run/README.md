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

The wrapper is the single place that loads `.local/runtime.env`, sources `.local/keys.env`, sets the DeepSeek proxy environment, sets the RSS feed, and redacts logs. Both `.local/` files are private and gitignored.

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

Store:

```text
.local/news-data/live-store.db
```

Logs:

```text
.local/news-data/logs/YYYY-MM-DD.log
```

Approximate run cost/time depends on new RSS items and generated clusters. A 6-item ServeTheHome run has taken a few minutes because each cluster can call DeepSeek for analysis, review, and target proposal.

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
