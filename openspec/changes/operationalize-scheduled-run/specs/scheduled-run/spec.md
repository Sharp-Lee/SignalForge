## ADDED Requirements

### Requirement: Self-contained Scheduled Wrapper

The system SHALL provide a scheduled-run wrapper that can execute the live pipeline without relying on an interactive shell environment. The wrapper MUST source keys at runtime, set the RSS feed URL, set proxy variables needed by DeepSeek, use an absolute project path, and run the pipeline against a persistent store.

#### Scenario: Wrapper runs from stripped environment
- **WHEN** the wrapper is run with only `HOME` and a minimal `PATH`
- **THEN** it sources runtime keys, configures the feed and proxy environment, and invokes `scripts/run_live.py --pipeline --store PATH`

#### Scenario: Wrapper keeps secrets out of static files
- **WHEN** the wrapper and scheduler configuration are inspected
- **THEN** they contain no API key values and only refer to the runtime key file path

### Requirement: Redacted Daily Logs

The scheduled wrapper SHALL append redacted output to a dated project-local log file under the gitignored local news data directory. The log MUST include enough operational context to diagnose runs without exposing secrets.

#### Scenario: Successful run appends log
- **WHEN** the scheduled wrapper runs
- **THEN** it appends redacted output to `.local/news-data/logs/YYYY-MM-DD.log`

#### Scenario: Failed run records exit code
- **WHEN** the scheduled wrapper fails
- **THEN** the log records the failure and the wrapper exits non-zero

### Requirement: User-session LaunchAgent

The system SHALL document and provide a macOS user LaunchAgent configuration for a daily scheduled run. The schedule MUST run in the user session so local proxy applications are available, and it MUST be reversible with documented unload and remove commands.

#### Scenario: LaunchAgent can be installed and verified
- **WHEN** the LaunchAgent plist is copied into `~/Library/LaunchAgents` and loaded
- **THEN** `launchctl list` can show the scheduled job label

#### Scenario: LaunchAgent can be disabled
- **WHEN** the documented unload and remove commands are run
- **THEN** the scheduled job is no longer registered

### Requirement: Operator Inspection

The operational run SHALL document how to inspect the persistent store and logs, and how to change the RSS feed without changing architecture-layer code.

#### Scenario: Operator inspects accumulated outputs
- **WHEN** the operator runs `scripts/run_live.py --show-store .local/news-data/live-store.db`
- **THEN** accumulated theses and targets are displayed

#### Scenario: Operator changes feed
- **WHEN** the feed setting is changed through the documented wrapper configuration path
- **THEN** the next scheduled run uses the new feed without code changes outside the operation layer
