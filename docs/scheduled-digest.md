# Scheduled Daily Digest Operations

SignalForge's live daily flow is:

1. Capture RSS sources four times per day: 08:30, 12:30, 16:30, 21:30.
2. Analyze pending signal clusters once per day at 18:00 local time.
3. Generate the Chinese research digest immediately after successful analysis.

The live store is `.local/news-data/live-store.db`. Logs are appended to
`.local/news-data/logs/YYYY-MM-DD.log`. Digest files are written to
`.local/news-data/digests/YYYY-MM-DD.md` and `.local/news-data/digests/YYYY-MM-DD.html`.

## Publish To WeChat Public Account

Open the generated HTML file in a browser, select the rendered content, and paste
it into the WeChat public-account editor. The HTML uses inline styles because
WeChat strips `<style>` and `<script>` tags. If formatting is still not accepted,
open the Markdown file and run it through a Markdown-to-WeChat editor such as
mdnice.

The digest is framed as personal research notes and includes a disclaimer. It
uses observation wording rather than buy/sell recommendations.

## Install Or Migrate LaunchAgents

```bash
mkdir -p "$HOME/Library/LaunchAgents"
launchctl bootout "gui/$(id -u)/com.wukong.news-pipeline" 2>/dev/null || true
rm -f "$HOME/Library/LaunchAgents/com.wukong.news-pipeline.plist"
cp launchd/com.wukong.news-capture.plist "$HOME/Library/LaunchAgents/"
cp launchd/com.wukong.news-analyze.plist "$HOME/Library/LaunchAgents/"
launchctl load "$HOME/Library/LaunchAgents/com.wukong.news-capture.plist"
launchctl load "$HOME/Library/LaunchAgents/com.wukong.news-analyze.plist"
launchctl list | grep 'com.wukong.news'
```

Only `com.wukong.news-capture` and `com.wukong.news-analyze` should be listed.

## Verify Manually

```bash
launchctl kickstart "gui/$(id -u)/com.wukong.news-capture"
launchctl kickstart -k "gui/$(id -u)/com.wukong.news-analyze"
tail -n 120 .local/news-data/logs/$(date +%F).log
python scripts/run_live.py --show-store .local/news-data/live-store.db
```

Look for `markdown=` and `html=` in the log. These are the generated digest
paths.

## Stop The Schedule

```bash
launchctl bootout "gui/$(id -u)/com.wukong.news-capture" 2>/dev/null || true
launchctl bootout "gui/$(id -u)/com.wukong.news-analyze" 2>/dev/null || true
rm -f "$HOME/Library/LaunchAgents/com.wukong.news-capture.plist"
rm -f "$HOME/Library/LaunchAgents/com.wukong.news-analyze.plist"
```
