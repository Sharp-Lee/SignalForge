## MODIFIED Requirements

### Requirement: Self-contained Scheduled Wrapper

The system SHALL provide scheduled-run wrappers or modes that execute capture and analyze independently without relying on an interactive shell environment. Capture MUST source runtime configuration and run configured feeds frequently. Analyze MUST source runtime configuration, run the pending analyze path against the persistent store, and generate the daily digest after analysis.

#### Scenario: Capture wrapper runs without analysis
- **WHEN** the scheduled capture command runs
- **THEN** it persists accepted signals and exits without invoking LLM analysis or target generation

#### Scenario: Analyze wrapper processes pending
- **WHEN** the scheduled analyze command runs
- **THEN** it analyzes pending signals up to the configured top-K budget and then generates the digest

### Requirement: User-session LaunchAgent

The system SHALL document and provide macOS user LaunchAgent configuration for frequent capture and daily analysis. Capture SHOULD run every 3-4 hours. Analyze SHOULD run once daily at 18:00 local time. Both jobs MUST be reversible with documented unload/remove commands.

#### Scenario: Capture LaunchAgent can be installed
- **WHEN** the capture LaunchAgent is copied and loaded
- **THEN** launchd can show the capture job label

#### Scenario: Analyze LaunchAgent can be installed
- **WHEN** the analyze LaunchAgent is copied and loaded
- **THEN** launchd can show the analyze job label
