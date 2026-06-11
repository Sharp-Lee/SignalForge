# SignalForge

SignalForge is a contract-first investment research pipeline that turns public signals into traceable theses and A-share watchlist candidates.

It is designed as a personal alpha tool:

```text
RSS / source ingestion
→ signal contracts and dedup
→ deterministic signal clustering
→ LLM thesis generation + adversarial review
→ target generation
→ real A-share universe and price lookup
→ persistent SQLite memory
→ scheduled macOS launchd run
```

## Public Repo Safety

This repository is public. Real API keys must stay outside the repo.

| Kind | Path | Git status |
|---|---|---|
| Secrets | `~/.config/news-llm/keys.env` | outside repo |
| Optional runtime overrides | `.local/runtime.env` | gitignored |
| Persistent store | `.local/news-data/live-store.db` | gitignored |
| Logs | `.local/news-data/logs/YYYY-MM-DD.log` | gitignored |
| Example config | `config/runtime.env.example` | committed |

Never put real keys in `.local/`, `config/`, docs, tests, or any committed file.

## First-Time Setup

Create the repo-external key file:

```bash
mkdir -p "$HOME/.config/news-llm"
chmod 700 "$HOME/.config/news-llm"
$EDITOR "$HOME/.config/news-llm/keys.env"
chmod 600 "$HOME/.config/news-llm/keys.env"
```

Required keys:

```text
DEEPSEEK_API_KEY=...
TUSHARE_TOKEN=...
```

Optional keys:

```text
RELAY_API_KEY=...
RELAY_BASE_URL=...
RELAY_FORMAT=...
RELAY_MODEL=...
RELAY_JSON_MODE=...
```

Create local runtime overrides if needed:

```bash
mkdir -p .local
cp config/runtime.env.example .local/runtime.env
chmod 600 .local/runtime.env
```

Run once:

```bash
bash scripts/run_scheduled.sh
```

Capture only:

```bash
python scripts/run_live.py --capture --store .local/news-data/live-store.db
```

Analyze pending only:

```bash
set -a; source "$HOME/.config/news-llm/keys.env"; set +a
python scripts/run_live.py --analyze --store .local/news-data/live-store.db
```

Inspect accumulated outputs:

```bash
python scripts/run_live.py --show-store .local/news-data/live-store.db
```

Generate a daily digest for review or manual public-account posting:

```bash
python scripts/generate_digest.py --store .local/news-data/live-store.db
```

This writes Markdown and WeChat-editor-friendly inline HTML under
`.local/news-data/digests/`. The digest groups content by logic chain:
source information -> supporting logic -> strongest counterargument -> selected
watchlist targets. It is a personal research note, not an investment
recommendation.

Open `.local/news-data/digests/YYYY-MM-DD.html` in a browser, select the rendered
content, and paste it into the WeChat public-account editor. If the editor strips
formatting, use the Markdown file with a Markdown-to-WeChat tool such as mdnice.

## Scheduled Run

The production schedule is split:

- `com.wukong.news-capture`: RSS capture only, four times per day: 08:30, 12:30, 16:30, 21:30.
- `com.wukong.news-analyze`: pending analysis + target generation + digest, daily at 18:00 after A-share close.

Both jobs call `scripts/run_scheduled.sh`; environment setup stays centralized in the wrapper. Capture does not require LLM or market-data keys. Analyze reads keys from `~/.config/news-llm/keys.env`, processes at most `NEWS_ANALYZE_TOP_K` pending clusters, skips stale pending items after `NEWS_PENDING_MAX_AGE_DAYS`, stops retrying repeatedly failing clusters after `NEWS_MAX_ANALYSIS_ATTEMPTS`, and writes `.local/news-data/digests/YYYY-MM-DD.md` plus `.html` after a successful run.

Install the LaunchAgents:

```bash
mkdir -p "$HOME/Library/LaunchAgents"
launchctl bootout "gui/$(id -u)/com.wukong.news-pipeline" 2>/dev/null || true
rm -f "$HOME/Library/LaunchAgents/com.wukong.news-pipeline.plist"
cp launchd/com.wukong.news-capture.plist "$HOME/Library/LaunchAgents/"
cp launchd/com.wukong.news-analyze.plist "$HOME/Library/LaunchAgents/"
launchctl load "$HOME/Library/LaunchAgents/com.wukong.news-capture.plist"
launchctl load "$HOME/Library/LaunchAgents/com.wukong.news-analyze.plist"
launchctl list | grep 'com.wukong.news-'
```

Trigger immediately for verification:

```bash
launchctl kickstart "gui/$(id -u)/com.wukong.news-capture"
launchctl kickstart "gui/$(id -u)/com.wukong.news-analyze"
```

Logs are written to `.local/news-data/logs/YYYY-MM-DD.log`.
Digest files are written to `.local/news-data/digests/YYYY-MM-DD.md` and
`.local/news-data/digests/YYYY-MM-DD.html`.

RSS sources are configured by `.local/rss_sources.json` or `NEWS_RSS_SOURCES_FILE`; copy `config/rss_sources.example.json` to customize. Quick one-off runs can use `RSS_FEED_URL`, `NEWS_RSS_FEED_URL`, or comma-separated `NEWS_RSS_FEED_URLS`.

Stop it:

```bash
launchctl unload "$HOME/Library/LaunchAgents/com.wukong.news-capture.plist"
launchctl unload "$HOME/Library/LaunchAgents/com.wukong.news-analyze.plist"
rm "$HOME/Library/LaunchAgents/com.wukong.news-capture.plist"
rm "$HOME/Library/LaunchAgents/com.wukong.news-analyze.plist"
```

## Validation

```bash
python -m pytest tests/ -q
openspec validate operationalize-scheduled-run --strict
openspec validate add-daily-digest --strict
openspec validate decouple-capture-analyze --strict
openspec validate schedule-digest-and-go-live --strict
```
