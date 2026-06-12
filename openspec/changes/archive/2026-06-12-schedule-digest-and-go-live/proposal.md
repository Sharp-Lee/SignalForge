# Change: schedule-digest-and-go-live

## Why

The scheduled pipeline is split into frequent capture and daily analyze, but the analyze wrapper currently stops after writing theses and targets. The user still has to run `scripts/generate_digest.py` manually, which breaks the intended daily-publication workflow.

The old coupled `com.wukong.news-pipeline` LaunchAgent can also coexist with the new split capture/analyze templates unless it is explicitly removed. That risks duplicate daily analysis and makes the live machine different from the checked-in operational model.

## What Changes

- Generate the daily digest automatically after successful scheduled analyze and pipeline runs.
- Keep capture runs signal-only and digest-free.
- Install the split LaunchAgents on the user machine and remove the old coupled pipeline job.
- Document the live daily flow, digest output paths, WeChat public-account handoff, and shutdown commands.

## Non-Goals

- No change to analysis, target generation, digest rendering logic, or contracts.
- No automatic public-account delivery.
- No archive in this change; reviewer will archive after live verification.
