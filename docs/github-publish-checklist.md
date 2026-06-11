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

- `.local/keys.env`
- `.local/runtime.env`
- `.local/news-data/*.db`
- `.local/news-data/logs/`
- API keys, webhook URLs, provider tokens

## Local Runtime Layout

The scheduled runner defaults to project-local private paths:

```text
.local/keys.env
.local/runtime.env
.local/news-data/live-store.db
.local/news-data/logs/YYYY-MM-DD.log
```

`.local/` is ignored by git.

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
