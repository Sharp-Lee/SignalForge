# scheduled-run Specification

## Purpose
TBD - created by archiving change operationalize-scheduled-run. Update Purpose after archive.
## Requirements
### Requirement: Self-contained Scheduled Wrapper

The system SHALL provide scheduled-run wrappers or modes that execute capture and analyze independently without relying on an interactive shell environment. Capture MUST source runtime configuration and run configured feeds frequently. Analyze MUST source runtime configuration, run the pending analyze path against the persistent store, and generate the daily digest after analysis.

#### Scenario: Capture wrapper runs without analysis
- **WHEN** the scheduled capture command runs
- **THEN** it persists accepted signals and exits without invoking LLM analysis or target generation

#### Scenario: Analyze wrapper processes pending
- **WHEN** the scheduled analyze command runs
- **THEN** it analyzes pending signals up to the configured top-K budget and then generates the digest

### Requirement: Redacted Daily Logs

The scheduled wrapper SHALL append redacted output to a dated project-local log file under the gitignored local news data directory. The log MUST include enough operational context to diagnose runs without exposing secrets.

#### Scenario: Successful run appends log
- **WHEN** the scheduled wrapper runs
- **THEN** it appends redacted output to `.local/news-data/logs/YYYY-MM-DD.log`

#### Scenario: Failed run records exit code
- **WHEN** the scheduled wrapper fails
- **THEN** the log records the failure and the wrapper exits non-zero

### Requirement: User-session LaunchAgent

The system SHALL document and provide macOS user LaunchAgent configuration for frequent capture and daily analysis. Capture SHOULD run every 3-4 hours. Analyze SHOULD run once daily at 18:00 local time. Both jobs MUST be reversible with documented unload/remove commands.

#### Scenario: Capture LaunchAgent can be installed
- **WHEN** the capture LaunchAgent is copied and loaded
- **THEN** launchd can show the capture job label

#### Scenario: Analyze LaunchAgent can be installed
- **WHEN** the analyze LaunchAgent is copied and loaded
- **THEN** launchd can show the analyze job label

### Requirement: Operator Inspection

The operational run SHALL document how to inspect the persistent store and logs, and how to change the RSS feed without changing architecture-layer code.

#### Scenario: Operator inspects accumulated outputs
- **WHEN** the operator runs `scripts/run_live.py --show-store .local/news-data/live-store.db`
- **THEN** accumulated theses and targets are displayed

#### Scenario: Operator changes feed
- **WHEN** the feed setting is changed through the documented wrapper configuration path
- **THEN** the next scheduled run uses the new feed without code changes outside the operation layer

