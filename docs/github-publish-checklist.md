# GitHub Publish Checklist

This project is intended to be publishable without local secrets or runtime data.

## Commit

Safe to commit:

- source code
- tests
- OpenSpec artifacts
- `config/runtime.env.example`
- `launchd/com.wukong.news-pipeline.plist`
- documentation

Never commit:

- `~/.config/news-llm/keys.env`
- any repo-local key copy such as `.local/keys.env`
- `.local/runtime.env`
- `.local/news-data/*.db`
- `.local/news-data/logs/`
- API keys, webhook URLs, provider tokens

## Local Runtime Layout

The scheduled runner defaults to project-local private paths:

```text
.local/runtime.env
.local/news-data/live-store.db
.local/news-data/logs/YYYY-MM-DD.log
```

`.local/` is ignored by git.

Secrets stay outside the repo:

```text
~/.config/news-llm/keys.env
```

That file should be mode `600` and contain `DEEPSEEK_API_KEY` and `TUSHARE_TOKEN`.

## Initial Git Setup

This folder is not currently a git repository. To publish:

```bash
git init
git add .
git status
git commit -m "Initial news investment pipeline"
git remote add origin <your-github-repo-url>
git push -u origin main
```

Before pushing, inspect `git status` and `git diff --cached --stat`. The `.local/` directory must not appear.
