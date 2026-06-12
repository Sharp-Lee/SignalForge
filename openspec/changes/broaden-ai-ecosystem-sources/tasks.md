## 1. Planning Cleanup

- [x] 1.1 Delete the unused `openspec/changes/add-openbb-research-adapter/` directory.

## 2. RSS Fetching

- [x] 2.1 Add browser-like request headers to the default RSS HTTP transport.
- [x] 2.2 Add an offline regression test proving the default HTTP transport builds a request with the expected User-Agent.

## 3. Source Configuration

- [x] 3.1 Add optional `domain` metadata to `RssSourceConfig` with backward-compatible loading.
- [x] 3.2 Broaden `config/rss_sources.example.json` to enabled hardware, energy, and AI technology sources verified with the project parser.
- [x] 3.3 Update source-config tests for enabled source ids, domain coverage, and quality/domain metadata.

## 4. Analysis Priority Hints

- [x] 4.1 Expand `_signal_score()` terms for energy, grid, data-center, cooling, storage, and AI software/adoption signals.
- [x] 4.2 Add offline tests for energy infrastructure and AI software priority hints.

## 5. Verification

- [x] 5.1 Run `python -m pytest tests/ -q`.
- [x] 5.2 Run `openspec validate broaden-ai-ecosystem-sources --strict`.
- [x] 5.3 Run a real capture against a temporary store and report per-source accepted counts plus sample titles across hardware, energy, and AI technology domains.
- [ ] 5.4 Scan staged files for secrets, commit, and push.
