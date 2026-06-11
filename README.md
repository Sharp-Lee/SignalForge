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

Inspect accumulated outputs:

```bash
python scripts/run_live.py --show-store .local/news-data/live-store.db
```

## Scheduled Run

Install the LaunchAgent:

```bash
mkdir -p "$HOME/Library/LaunchAgents"
cp launchd/com.wukong.news-pipeline.plist "$HOME/Library/LaunchAgents/"
launchctl load "$HOME/Library/LaunchAgents/com.wukong.news-pipeline.plist"
launchctl list | grep com.wukong.news-pipeline
```

It runs daily at 18:00 local time and calls `scripts/run_scheduled.sh`.

Stop it:

```bash
launchctl unload "$HOME/Library/LaunchAgents/com.wukong.news-pipeline.plist"
rm "$HOME/Library/LaunchAgents/com.wukong.news-pipeline.plist"
```

## Validation

```bash
python -m pytest tests/ -q
openspec validate operationalize-scheduled-run --strict
```
