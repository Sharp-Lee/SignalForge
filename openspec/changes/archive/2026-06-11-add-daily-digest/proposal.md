## Why

The scheduled pipeline now accumulates theses, targets, and track records in a persistent local store, but there is no reader-facing daily artifact. The next delivery channel is a personal WeChat public account, so the system needs a deterministic digest generator before any delivery integration.

## What Changes

- Add a read-only daily digest CLI that reads the persistent SQLite store and writes Markdown plus inline-style HTML.
- Summarize same-day newly created theses and the current watchlist in Chinese, framed as personal research notes.
- Include the strongest counterargument for each thesis and clear investment-risk disclaimer text.
- Handle empty stores or no same-day content by generating a short "no new content" digest.

## Non-Goals

- No WeChat/official-account delivery API.
- No LLM rewriting or translation during digest generation.
- No mutation of the persistent store.
- No changes to pipeline, storage schema, analysis, target generation, market data, or scheduled run behavior.
