## 1. OpenSpec

- [x] Write proposal, design, scheduled-run delta spec, and tasks.

## 2. Wrapper

- [x] Generate the daily digest after successful analyze and pipeline runs.
- [x] Keep capture runs digest-free.
- [x] Preserve redacted dated logging and non-zero failure behavior.

## 3. Tests And Docs

- [x] Update scheduled-run asset tests for digest behavior.
- [x] Document daily digest scheduling, output paths, WeChat handoff, and stop commands.

## 4. Live Migration

- [x] Remove old `com.wukong.news-pipeline` LaunchAgent if installed.
- [x] Install and load `com.wukong.news-capture` and `com.wukong.news-analyze`.
- [x] Kickstart real launchd analyze and verify digest output in logs.

## 5. Verification

- [x] `bash -n scripts/run_scheduled.sh`
- [x] `python -m pytest tests/ -q`
- [x] `openspec validate schedule-digest-and-go-live --strict`
- [x] Secret scan, commit, and push.
