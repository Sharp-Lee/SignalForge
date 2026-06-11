## 1. R1 Gate: Stripped Environment Proof

- [x] 1.1 Add proposal and scheduled-run contract delta
- [x] 1.2 Add a self-contained wrapper script for proof execution
- [x] 1.3 Run the wrapper under `env -i HOME="$HOME" PATH="/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin"`
- [x] 1.4 Record redacted evidence in `design.md`
- [x] 1.5 Stop for reviewer approval before installing launchd

## 2. Implementation After Gate Approval

- [x] 2.1 Add repo-local LaunchAgent plist template for daily 18:00 user-session run
- [x] 2.2 Install the LaunchAgent into `~/Library/LaunchAgents`
- [x] 2.3 Verify registration with `launchctl list`
- [x] 2.4 Document unload/remove commands
- [x] 2.5 Document logs, store path, show-store inspection, and feed override

## 3. Verification

- [x] 3.1 Run offline tests for wrapper/plist behavior where practical
- [x] 3.2 Run `openspec validate operationalize-scheduled-run --strict`
- [x] 3.3 Perform a manual scheduled wrapper run after launchd installation
- [x] 3.4 Do not archive until reviewer approval

## 4. Public Repo Secret Hardening

- [x] 4.1 Move real keys back outside the repo to `~/.config/news-llm/keys.env`
- [x] 4.2 Remove repo-local `.local/keys.env`
- [x] 4.3 Change wrapper default `NEWS_KEYS_FILE` back to repo-external path
- [x] 4.4 Ensure wrapper creates key/store/log parent directories and prints clear missing-key guidance
- [x] 4.5 Update public docs and runtime example with repo-external key layout
- [x] 4.6 Verify stripped-environment run with a temporary store
- [x] 4.7 Verify launchd still points to wrapper
- [ ] 4.8 Run tests, OpenSpec strict validation, and staged secret scan before push
